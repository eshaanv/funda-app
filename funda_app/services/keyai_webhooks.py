import logging

from funda_app.schemas.crm import (
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioSyncResult,
    AttioPersonSyncPayload,
)
from funda_app.schemas.webhooks import (
    BaseMemberWebhookPayload,
    MemberJoinedWebhookPayload,
    MemberWebhookPayload,
    MemberWebhookEvent,
    WebhookAcceptedResponse,
)
from funda_app.schemas.whatsapp import (
    WhatsAppDispatchResult,
    WhatsAppTemplateName,
    WhatsAppTemplateSendRequest,
)
from funda_app.services.attio import normalize_phone_number, sync_attio_member
from funda_app.services.keyai_questions import (
    KeyaiQuestionField,
    get_question_answer,
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
    template_name = _get_whatsapp_template_name(payload)

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
    company_name = _get_company_name(payload)
    company_stage = _get_company_stage(payload)
    company_website = _get_company_website_domain(payload)
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
            keyai_member_id=payload.member.id,
            email=payload.member.email,
            full_name=payload.member.fullName,
            first_name=payload.member.firstName,
            last_name=payload.member.lastName,
            phone=normalize_phone_number(payload.member.phone),
            linkedin_url=_get_linkedin_url(payload),
            job_title=_get_job_title(payload),
        ),
        company=company,
    )


def dispatch_keyai_member_tasks(payload: BaseMemberWebhookPayload) -> None:
    """
    Runs background member tasks in the intended order.

    Args:
        payload (BaseMemberWebhookPayload): Validated member webhook payload.
    """
    dispatch_keyai_attio_sync(payload)

    if payload.event == MemberWebhookEvent.MEMBER_JOINED:
        # TODO: Enable joined-member enrichment once we have a stable way to test it.
        dispatch_keyai_whatsapp_message(payload)
        return

    dispatch_keyai_whatsapp_message(payload)


def dispatch_keyai_joined_member_tasks(payload: MemberJoinedWebhookPayload) -> None:
    """
    Runs joined-member background tasks in the intended order.

    Args:
        payload (MemberJoinedWebhookPayload): Joined member webhook payload.
    """
    dispatch_keyai_member_tasks(payload)


def dispatch_keyai_attio_sync(payload: BaseMemberWebhookPayload) -> None:
    """
    Syncs a Key.ai lifecycle event into Attio.

    Args:
        payload (BaseMemberWebhookPayload): Validated Key.ai webhook payload.
    """
    sync_request = build_keyai_attio_sync_request(payload)

    try:
        result = sync_attio_member(sync_request)
    except Exception:
        logger.exception(
            "Attio sync failed: event=%s member_id=%s event_id=%s",
            payload.event,
            payload.member.id,
            payload.eventId,
        )
        return

    _log_attio_sync_result(payload, result)


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

    _log_dispatch_result(payload, send_request, result)


def _log_dispatch_result(
    payload: BaseMemberWebhookPayload,
    send_request: WhatsAppTemplateSendRequest,
    result: WhatsAppDispatchResult,
) -> None:
    """
    Logs the result of a WhatsApp dispatch attempt.

    Args:
        payload (BaseMemberWebhookPayload): Source Key.ai webhook payload.
        send_request (WhatsAppTemplateSendRequest): Outbound send request.
        result (WhatsAppDispatchResult): Provider dispatch result.
    """
    logger.info(
        "WhatsApp dispatch completed: event=%s member_id=%s template=%s status=%s message_id=%s",
        payload.event,
        payload.member.id,
        send_request.template_name,
        result.status,
        result.message_id,
    )


def _log_attio_sync_result(
    payload: BaseMemberWebhookPayload,
    result: AttioSyncResult,
) -> None:
    """
    Logs the result of an Attio sync attempt.

    Args:
        payload (BaseMemberWebhookPayload): Source Key.ai webhook payload.
        result (AttioSyncResult): Attio sync result.
    """
    logger.info(
        "Attio sync completed: event=%s member_id=%s person_record_id=%s company_record_id=%s lifecycle_entry_id=%s",
        payload.event,
        payload.member.id,
        result.person_record_id,
        result.company_record_id or "",
        result.lifecycle_entry_id,
    )


def _get_whatsapp_template_name(
    payload: BaseMemberWebhookPayload,
) -> WhatsAppTemplateName | None:
    if payload.event == MemberWebhookEvent.MEMBER_JOINED:
        return WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION

    if payload.event == MemberWebhookEvent.MEMBER_APPROVED:
        return WhatsAppTemplateName.FUNDA_MEMBERSHIP_APPROVED

    if payload.event == MemberWebhookEvent.MEMBER_REJECTED:
        return WhatsAppTemplateName.FUNDA_MEMBERSHIP_REJECTED

    return None


def _get_linkedin_url(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.linkedinUrl and payload.member.linkedinUrl.strip():
        return payload.member.linkedinUrl.strip()

    value = get_question_answer(payload.questions, KeyaiQuestionField.LINKEDIN_URL)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_company_name(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.companyName and payload.member.companyName.strip():
        return payload.member.companyName.strip()

    value = get_question_answer(payload.questions, KeyaiQuestionField.COMPANY_NAME)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_company_stage(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.companyStage and payload.member.companyStage.strip():
        return payload.member.companyStage.strip()

    value = get_question_answer(payload.questions, KeyaiQuestionField.FUNDING_STAGE)
    if value is None or not value.strip():
        return None
    return value.strip()


def _get_job_title(payload: BaseMemberWebhookPayload) -> str | None:
    return get_question_answer(payload.questions, KeyaiQuestionField.JOB_TITLE)


def _get_company_website_domain(payload: BaseMemberWebhookPayload) -> str | None:
    return get_question_answer(
        payload.questions, KeyaiQuestionField.COMPANY_WEBSITE_DOMAIN
    )
