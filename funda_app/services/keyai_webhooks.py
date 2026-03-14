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
    MemberQuestionPayload,
    WebhookAcceptedResponse,
)
from funda_app.schemas.whatsapp import (
    WhatsAppDispatchResult,
    WhatsAppTemplateName,
    WhatsAppTemplateSendRequest,
)
from funda_app.services.attio import normalize_phone_number, sync_attio_member
from funda_app.services.member_enrichment import dispatch_member_joined_enrichment
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
    if payload.event != MemberWebhookEvent.MEMBER_JOINED:
        return None

    if not payload.member.phone.strip():
        return None

    return WhatsAppTemplateSendRequest(
        to=payload.member.phone,
        template_name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
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
    company = None

    if company_name is not None:
        company = AttioCompanySyncPayload(
            name=company_name,
            stage=company_stage,
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

    if payload.event != MemberWebhookEvent.MEMBER_JOINED:
        return

    dispatch_member_joined_enrichment(payload)
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


def _get_linkedin_url(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.linkedinUrl and payload.member.linkedinUrl.strip():
        return payload.member.linkedinUrl.strip()

    question_value = _find_answer(payload.questions, "linked")
    if question_value is None or not question_value.strip():
        return None

    return question_value.strip()


def _get_company_name(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.companyName and payload.member.companyName.strip():
        return payload.member.companyName.strip()

    question_value = _find_answer(payload.questions, "company name")
    if question_value is None or not question_value.strip():
        return None

    return question_value.strip()


def _get_company_stage(payload: BaseMemberWebhookPayload) -> str | None:
    if payload.member.companyStage and payload.member.companyStage.strip():
        return payload.member.companyStage.strip()

    question_value = _find_answer(payload.questions, "funding stage")
    if question_value is None or not question_value.strip():
        return None

    return question_value.strip()


def _find_answer(
    questions: list[MemberQuestionPayload] | None,
    pattern: str,
) -> str | None:
    if questions is None:
        return None

    lowered_pattern = pattern.lower()

    for item in questions:
        if lowered_pattern in item.question.lower():
            return item.answer

    return None
