import logging

from google.genai.types import GenerateContentConfig

from funda_app.agents.models import invoke_gemini
from funda_app.agents.prompt import (
    NEW_MEMBER_ADMIN_BLURBS_PROMPT_TEMPLATE,
)
from funda_app.schemas.admin_notification import AdminNotificationBlurbs
from funda_app.schemas.crm import (
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioPersonSyncPayload,
)
from funda_app.schemas.webhooks import (
    BaseMemberWebhookPayload,
    MemberWebhookEvent,
    MemberWebhookPayload,
    WebhookAcceptedResponse,
)
from funda_app.schemas.whatsapp import (
    WhatsAppTemplateSendRequest,
    WhatsAppTemplateName,
    whatsapp_template_name_for_event,
)
from funda_app.app_settings import AppSettings, get_app_settings
from funda_app.core import sanitize_whatsapp_text
from funda_app.utils import normalize_phone_number
from funda_app.services.attio import (
    get_member_context_for_member,
    get_phone_number_for_member,
    sync_attio_lifecycle_only,
    sync_attio_member,
)
from funda_app.services.idempotency import (
    begin_keyai_event_processing,
    mark_keyai_event_attio_done,
    mark_keyai_event_admin_notification_done,
    mark_keyai_event_completed,
    mark_keyai_event_failed,
    mark_keyai_event_whatsapp_done,
)
from funda_app.services.keyai_questions import (
    get_company_name,
    get_company_stage,
    get_company_website,
    get_job_title,
    get_linkedin_url,
    get_whatsapp_phone_number,
)
from funda_app.services.whatsapp import send_whatsapp_template_message

logger = logging.getLogger(__name__)


def _resolve_phone_number(payload: BaseMemberWebhookPayload) -> str | None:
    """
    Resolves the member phone number from questions first, then member fields.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        str | None: Resolved phone number, or None when unavailable.
    """
    return get_whatsapp_phone_number(payload.questions) or payload.member.phone


def _resolve_whatsapp_phone_number(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> str | None:
    """
    Resolves the WhatsApp destination phone number for a webhook event.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
        settings (AppSettings | None, optional): Explicit runtime settings.
            Defaults to None.

    Returns:
        str | None: Resolved WhatsApp destination number, or None when unavailable.
    """
    if payload.event == MemberWebhookEvent.MEMBER_JOINED:
        return _resolve_phone_number(payload)

    return get_phone_number_for_member(
        member_id=payload.member.id,
        settings=settings,
    )


def _resolve_linkedin_url(payload: BaseMemberWebhookPayload) -> str | None:
    """
    Resolves LinkedIn URL from questions first, then member fields.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        str | None: Resolved LinkedIn URL, or None when unavailable.
    """
    return get_linkedin_url(payload.questions) or payload.member.linkedinUrl


def _resolve_company_name(payload: BaseMemberWebhookPayload) -> str | None:
    """
    Resolves company name from questions.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        str | None: Resolved company name, or None when unavailable.
    """
    return get_company_name(payload.questions)


def _resolve_company_stage(payload: BaseMemberWebhookPayload) -> str | None:
    """
    Resolves company stage from questions.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        str | None: Resolved company stage, or None when unavailable.
    """
    return get_company_stage(payload.questions)


def _get_non_joined_member_context(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
):
    """
    Returns canonical Attio member context for non-joined events.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
        settings (AppSettings | None, optional): Explicit runtime settings.
            Defaults to None.

    Returns:
        object | None: Attio member context when available, otherwise None.
    """
    if payload.event == MemberWebhookEvent.MEMBER_JOINED:
        return None

    return get_member_context_for_member(
        member_id=payload.member.id,
        settings=settings,
    )


def handle_keyai_webhook(payload: MemberWebhookPayload) -> WebhookAcceptedResponse:
    """
    Handles all webhook payloads received from Key.ai.

    Args:
        payload (MemberWebhookPayload): Validated webhook payload sent by Key.ai.

    Returns:
        WebhookAcceptedResponse: The acknowledgment returned to the webhook caller.
    """
    return _process_event(payload)


def _process_event(payload: BaseMemberWebhookPayload) -> WebhookAcceptedResponse:
    """
    Processes a validated Key.ai member webhook payload.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        WebhookAcceptedResponse: The acknowledgment returned to the webhook caller.
    """
    return WebhookAcceptedResponse(
        event=payload.event,
        user_id=payload.member.id,
    )


def build_keyai_whatsapp_send_request(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> WhatsAppTemplateSendRequest | None:
    """
    Builds a WhatsApp template send request for a supported Key.ai event.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
        settings (AppSettings | None, optional): Explicit runtime settings.
            Defaults to None.

    Returns:
        WhatsAppTemplateSendRequest | None: Template send request for supported
            events, otherwise None.
    """
    template_name = whatsapp_template_name_for_event(payload.event)

    if template_name is None:
        logger.info(
            "Skipping WhatsApp dispatch: no template mapping: event=%s member_id=%s event_id=%s community_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return None

    phone_number = (
        _resolve_whatsapp_phone_number(
            payload=payload,
            settings=settings,
        )
        or ""
    )

    if not (phone_number or "").strip():
        logger.info(
            "Skipping WhatsApp dispatch: missing phone: event=%s member_id=%s event_id=%s community_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return None

    return WhatsAppTemplateSendRequest(
        to=phone_number,
        template_name=template_name,
        template_metadata={
            "first_name": payload.member.firstName,
        },
    )


def build_keyai_attio_sync_request(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> AttioLifecycleSyncRequest:
    """
    Builds an Attio lifecycle sync request for a validated Key.ai event.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        AttioLifecycleSyncRequest: Normalized Attio sync request.
    """
    member = payload.member
    questions = payload.questions
    member_context = _get_non_joined_member_context(
        payload=payload,
        settings=settings,
    )

    if payload.event == MemberWebhookEvent.MEMBER_JOINED:
        company_name = _resolve_company_name(payload)
        company_stage = _resolve_company_stage(payload)
        company_website = get_company_website(questions)
        phone_number = _resolve_phone_number(payload)
        linkedin_url = _resolve_linkedin_url(payload)
        job_title = get_job_title(questions)
    else:
        company_name = member_context.company_name if member_context else None
        company_stage = member_context.company_stage if member_context else None
        company_website = None
        phone_number = member_context.phone if member_context else None
        linkedin_url = member_context.linkedin_url if member_context else None
        job_title = member_context.job_title if member_context else None

    company = None

    if company_name is not None:
        company = AttioCompanySyncPayload(
            name=company_name,
            stage=company_stage,
            company_website=company_website,
        )

    return AttioLifecycleSyncRequest(
        event=payload.event,
        event_id=payload.eventId,
        occurred_at=payload.occurredAt,
        community_id=payload.community.id,
        community_name=payload.community.name,
        member_status=payload.status.new,
        person=AttioPersonSyncPayload(
            keyai_member_id=member.id,
            email=member.email,
            full_name=member.fullName,
            first_name=member.firstName,
            last_name=member.lastName,
            phone=normalize_phone_number(phone_number),
            linkedin_url=linkedin_url,
            job_title=job_title,
        ),
        company=company,
    )


def dispatch_keyai_member_tasks(payload: BaseMemberWebhookPayload) -> None:
    """
    Runs background member tasks in the intended order.

    Args:
        payload (BaseMemberWebhookPayload): Validated member webhook payload.
    """
    try:
        processing_state = begin_keyai_event_processing(
            event_id=payload.eventId,
            member_id=payload.member.id,
            event_type=payload.event.value,
        )
    except Exception:
        logger.exception(
            "Key.ai event claim failed: event=%s member_id=%s event_id=%s community_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return

    if not processing_state.should_process:
        logger.info(
            "Skipping duplicate member event: event=%s member_id=%s event_id=%s community_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return

    try:
        if not processing_state.attio_done:
            if not dispatch_keyai_attio_sync(payload):
                mark_keyai_event_failed(
                    event_id=payload.eventId,
                    error_message="attio_sync_failed",
                )
                return
            mark_keyai_event_attio_done(payload.eventId)

        if not processing_state.whatsapp_done:
            if not dispatch_keyai_whatsapp_message(payload):
                mark_keyai_event_failed(
                    event_id=payload.eventId,
                    error_message="whatsapp_dispatch_failed",
                )
                return
            mark_keyai_event_whatsapp_done(payload.eventId)

        if (
            payload.event == MemberWebhookEvent.MEMBER_APPROVED
            and not processing_state.admin_notification_done
        ):
            if not dispatch_new_member_admin_notification(payload):
                mark_keyai_event_failed(
                    event_id=payload.eventId,
                    error_message="admin_notification_failed",
                )
                return
            mark_keyai_event_admin_notification_done(payload.eventId)

        mark_keyai_event_completed(payload.eventId)
    except Exception:
        logger.exception(
            "Key.ai event progress update failed: event=%s member_id=%s event_id=%s community_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return


def dispatch_keyai_attio_sync(payload: BaseMemberWebhookPayload) -> bool:
    """
    Syncs a Key.ai lifecycle event into Attio.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    sync_request = build_keyai_attio_sync_request(payload)

    try:
        if payload.event == MemberWebhookEvent.MEMBER_JOINED:
            result = sync_attio_member(sync_request)
        else:
            result = sync_attio_lifecycle_only(sync_request)
    except Exception as exc:
        logger.exception(
            "Attio sync failed: event=%s member_id=%s event_id=%s community_id=%s error=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
            str(exc),
        )
        return False

    logger.info(
        "Attio sync completed: event=%s member_id=%s event_id=%s community_id=%s person_record_id=%s company_record_id=%s lifecycle_entry_id=%s",
        payload.event,
        payload.member.id,
        payload.eventId,
        payload.community.id,
        result.person_record_id,
        result.company_record_id or "",
        result.lifecycle_entry_id,
    )
    return True


def dispatch_keyai_whatsapp_message(payload: BaseMemberWebhookPayload) -> bool:
    """
    Dispatches a Key.ai-triggered WhatsApp template message.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    send_request = build_keyai_whatsapp_send_request(payload)

    if send_request is None:
        return True

    try:
        result = send_whatsapp_template_message(send_request)
    except Exception:
        logger.exception(
            "WhatsApp dispatch failed: event=%s member_id=%s event_id=%s community_id=%s template=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
            send_request.template_name,
        )
        return False

    logger.info(
        "WhatsApp dispatch completed: event=%s member_id=%s event_id=%s community_id=%s template=%s status=%s message_id=%s",
        payload.event,
        payload.member.id,
        payload.eventId,
        payload.community.id,
        send_request.template_name,
        result.status,
        result.message_id,
    )
    return True


def build_new_member_admin_notification_request(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> WhatsAppTemplateSendRequest | None:
    """
    Builds an admin notification request for approved members.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
        settings (AppSettings | None, optional): Explicit runtime settings.
            Defaults to None.

    Returns:
        WhatsAppTemplateSendRequest | None: Admin notification request for
            approved members, otherwise None.
    """
    if payload.event != payload.event.MEMBER_APPROVED:
        return None

    runtime_settings = settings or get_app_settings()

    if not runtime_settings.new_member_admin_phone:
        logger.info(
            "Skipping admin notification: missing new_member_admin_phone: member_id=%s event_id=%s community_id=%s",
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )
        return None

    blurbs = build_new_member_admin_blurbs(payload)

    return WhatsAppTemplateSendRequest(
        to=runtime_settings.new_member_admin_phone,
        template_name=WhatsAppTemplateName.FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION,
        template_metadata={
            "full_name": payload.member.fullName,
            "member_sentence": blurbs.individual_blurb,
            "company_sentence": blurbs.company_blurb,
        },
    )


def build_new_member_admin_blurbs(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> AdminNotificationBlurbs:
    """
    Builds the member and company blurbs for the admin notification.

    Args:
        payload (BaseMemberWebhookPayload): Approved Key.ai webhook payload.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        AdminNotificationBlurbs: Structured admin notification blurbs.
    """
    member_context = None
    try:
        member_context = get_member_context_for_member(
            member_id=payload.member.id,
            settings=settings,
        )
    except Exception:
        logger.exception(
            "Attio member context lookup failed for admin notification: member_id=%s event_id=%s community_id=%s",
            payload.member.id,
            payload.eventId,
            payload.community.id,
        )

    company_name = member_context.company_name if member_context else None
    if not company_name:
        return AdminNotificationBlurbs(
            individual_blurb=sanitize_whatsapp_text(
                f"{payload.member.fullName} is an approved member of the Funda community."
            ),
            company_blurb="Company not found",
        )

    prompt = NEW_MEMBER_ADMIN_BLURBS_PROMPT_TEMPLATE.format(
        full_name=payload.member.fullName,
        first_name=payload.member.firstName,
        last_name=payload.member.lastName,
        linkedin_url=(
            member_context.linkedin_url
            if member_context and member_context.linkedin_url is not None
            else "unknown"
        ),
        company_name=company_name,
        company_stage=(
            member_context.company_stage
            if member_context and member_context.company_stage is not None
            else "unknown"
        ),
        company_website=(
            member_context.company_website
            if member_context and member_context.company_website is not None
            else "unknown"
        ),
        occurred_at=payload.occurredAt.isoformat(),
        company_description="unknown",
        role=(
            member_context.job_title
            if member_context and member_context.job_title is not None
            else "unknown"
        ),
    )
    response = invoke_gemini(
        prompt=prompt,
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AdminNotificationBlurbs.model_json_schema(),
        ),
    )

    if response is None:
        return AdminNotificationBlurbs(
            individual_blurb=sanitize_whatsapp_text(
                f"{payload.member.fullName} works at {company_name}."
            ),
            company_blurb=sanitize_whatsapp_text(
                f"{company_name} is the company associated with this member."
            ),
        )

    try:
        blurbs = AdminNotificationBlurbs.model_validate_json(response)
    except Exception:
        logger.warning(
            "Admin notification blurbs response was not valid JSON: event=%s member_id=%s event_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
        )
        return AdminNotificationBlurbs(
            individual_blurb=sanitize_whatsapp_text(
                f"{payload.member.fullName} works at {company_name}."
            ),
            company_blurb=sanitize_whatsapp_text(
                f"{company_name} is the company associated with this member."
            ),
        )

    return AdminNotificationBlurbs(
        individual_blurb=sanitize_whatsapp_text(blurbs.individual_blurb),
        company_blurb=sanitize_whatsapp_text(blurbs.company_blurb),
        citations=blurbs.citations,
    )


def build_new_member_admin_member_sentence(
    payload: BaseMemberWebhookPayload,
) -> str:
    """
    Builds the factual member intro sentence for the admin notification.

    Args:
        payload (BaseMemberWebhookPayload): Approved Key.ai webhook payload.

    Returns:
        str: Factual member intro sentence.
    """
    return build_new_member_admin_blurbs(payload).individual_blurb


def build_new_member_admin_company_sentence(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> str:
    """
    Builds the factual company sentence for the admin notification.

    Args:
        payload (BaseMemberWebhookPayload): Approved Key.ai webhook payload.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        str: Factual company sentence or fixed fallback text.
    """
    return build_new_member_admin_blurbs(
        payload=payload,
        settings=settings,
    ).company_blurb


def dispatch_new_member_admin_notification(payload: BaseMemberWebhookPayload) -> bool:
    """
    Dispatches an approved-member admin notification.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    send_request = build_new_member_admin_notification_request(payload)

    if send_request is None:
        return True

    try:
        result = send_whatsapp_template_message(send_request)
    except Exception:
        logger.exception(
            "Admin notification failed: event=%s member_id=%s event_id=%s community_id=%s template=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            payload.community.id,
            send_request.template_name,
        )
        return False

    logger.info(
        "Admin notification completed: event=%s member_id=%s event_id=%s community_id=%s template=%s status=%s message_id=%s",
        payload.event,
        payload.member.id,
        payload.eventId,
        payload.community.id,
        send_request.template_name,
        result.status,
        result.message_id,
    )
    return True
