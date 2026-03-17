import logging

from funda_app.agents.models import invoke_gemini
from funda_app.agents.prompt import (
    NEW_MEMBER_ADMIN_COMPANY_PROMPT_TEMPLATE,
    NEW_MEMBER_ADMIN_NOTIFICATION_PROMPT_TEMPLATE,
)
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
from funda_app.utils import normalize_phone_number
from funda_app.services.attio import (
    get_latest_lifecycle_event_id_for_member,
    get_linked_company_name_for_member,
    sync_attio_member,
)
from funda_app.services.keyai_questions import (
    get_company_name,
    get_company_stage,
    get_company_website_domain,
    get_job_title,
    get_linkedin_url,
)
from funda_app.services.whatsapp import send_whatsapp_template_message

logger = logging.getLogger(__name__)


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
) -> WhatsAppTemplateSendRequest | None:
    """
    Builds a WhatsApp template send request for a supported Key.ai event.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.

    Returns:
        WhatsAppTemplateSendRequest | None: Template send request for supported
            events, otherwise None.
    """
    template_name = whatsapp_template_name_for_event(payload.event)

    if template_name is None:
        return None

    if not payload.member.phone.strip():
        return None

    return WhatsAppTemplateSendRequest(
        to=payload.member.phone,
        template_name=template_name,
        template_metadata={
            "first_name": payload.member.firstName,
        },
    )


def build_keyai_attio_sync_request(
    payload: BaseMemberWebhookPayload,
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
    company_name = get_company_name(member.companyName, questions)
    company_stage = get_company_stage(member.companyStage, questions)
    company_website = get_company_website_domain(questions)
    company = None

    if (
        payload.event == MemberWebhookEvent.MEMBER_JOINED
        and company_name is not None
    ):
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
            phone=normalize_phone_number(member.phone),
            linkedin_url=get_linkedin_url(member.linkedinUrl, questions),
            job_title=get_job_title(questions),
        ),
        company=company,
    )


def dispatch_keyai_member_tasks(payload: BaseMemberWebhookPayload) -> None:
    """
    Runs background member tasks in the intended order.

    Args:
        payload (BaseMemberWebhookPayload): Validated member webhook payload.
    """
    if is_duplicate_keyai_member_event(payload):
        logger.info(
            "Skipping duplicate member event: event=%s member_id=%s event_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
        )
        return

    dispatch_keyai_attio_sync(payload)
    dispatch_keyai_whatsapp_message(payload)


def is_duplicate_keyai_member_event(
    payload: BaseMemberWebhookPayload,
    settings: AppSettings | None = None,
) -> bool:
    """
    Returns whether a Key.ai member event was already processed.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        bool: True when the lifecycle record already contains the same event ID.
    """
    try:
        latest_event_id = get_latest_lifecycle_event_id_for_member(
            member_id=payload.member.id,
            settings=settings,
        )
    except Exception as exc:
        logger.warning(
            "Duplicate check failed; continuing without dedupe: event=%s member_id=%s event_id=%s error=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            str(exc),
        )
        return False

    return latest_event_id == payload.eventId


def dispatch_keyai_attio_sync(payload: BaseMemberWebhookPayload) -> None:
    """
    Syncs a Key.ai lifecycle event into Attio.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    sync_request = build_keyai_attio_sync_request(payload)

    try:
        result = sync_attio_member(sync_request)
    except Exception as exc:
        logger.exception(
            "Attio sync failed: event=%s member_id=%s event_id=%s error=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
            str(exc),
        )
        return

    logger.info(
        "Attio sync completed: event=%s member_id=%s person_record_id=%s company_record_id=%s lifecycle_entry_id=%s",
        payload.event,
        payload.member.id,
        result.person_record_id,
        result.company_record_id or "",
        result.lifecycle_entry_id,
    )


def dispatch_keyai_whatsapp_message(payload: BaseMemberWebhookPayload) -> None:
    """
    Dispatches a Key.ai-triggered WhatsApp template message.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    send_request = build_keyai_whatsapp_send_request(payload)

    if send_request is None:
        logger.info(
            "Skipping WhatsApp dispatch: event=%s member_id=%s",
            payload.event,
            payload.member.id,
        )
        return

    try:
        result = send_whatsapp_template_message(send_request)
    except Exception:
        logger.exception(
            "WhatsApp dispatch failed: event=%s member_id=%s template=%s",
            payload.event,
            payload.member.id,
            send_request.template_name,
        )
        return

    logger.info(
        "WhatsApp dispatch completed: event=%s member_id=%s template=%s status=%s message_id=%s",
        payload.event,
        payload.member.id,
        send_request.template_name,
        result.status,
        result.message_id,
    )


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
        return None

    return WhatsAppTemplateSendRequest(
        to=runtime_settings.new_member_admin_phone,
        template_name=WhatsAppTemplateName.FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION,
        template_metadata={
            "full_name": payload.member.fullName,
            "member_sentence": build_new_member_admin_member_sentence(payload),
            "company_sentence": build_new_member_admin_company_sentence(payload),
        },
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
    prompt = NEW_MEMBER_ADMIN_NOTIFICATION_PROMPT_TEMPLATE.format(
        full_name=payload.member.fullName,
        first_name=payload.member.firstName,
        last_name=payload.member.lastName,
        email=payload.member.email,
        phone=payload.member.phone,
        company_name=payload.member.companyName or "unknown",
        company_stage=payload.member.companyStage or "unknown",
        community_name=payload.community.name,
        occurred_at=payload.occurredAt.isoformat(),
    )
    response = invoke_gemini(
        prompt=prompt,
    )
    return (response or f"{payload.member.fullName} is an approved member of the Funda community.").strip()


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
    company_name = payload.member.companyName
    if not company_name:
        try:
            company_name = get_linked_company_name_for_member(
                member_id=payload.member.id,
                settings=settings,
            )
        except Exception:
            logger.exception(
                "Attio company lookup failed for admin notification: member_id=%s",
                payload.member.id,
            )

    if not company_name:
        return "Company not found"

    prompt = NEW_MEMBER_ADMIN_COMPANY_PROMPT_TEMPLATE.format(
        company_name=company_name,
        community_name=payload.community.name,
    )
    response = invoke_gemini(
        prompt=prompt,
    )
    return (response or f"{company_name} is the company associated with this member.").strip()


def dispatch_new_member_admin_notification(payload: BaseMemberWebhookPayload) -> None:
    """
    Dispatches an approved-member admin notification.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    send_request = build_new_member_admin_notification_request(payload)

    if send_request is None:
        return

    try:
        result = send_whatsapp_template_message(send_request)
    except Exception:
        logger.exception(
            "Admin notification failed: event=%s member_id=%s template=%s",
            payload.event,
            payload.member.id,
            send_request.template_name,
        )
        return

    logger.info(
        "Admin notification completed: event=%s member_id=%s template=%s status=%s message_id=%s",
        payload.event,
        payload.member.id,
        send_request.template_name,
        result.status,
        result.message_id,
    )
