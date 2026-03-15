import logging

from funda_app.schemas.crm import (
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioPersonSyncPayload,
)
from funda_app.schemas.webhooks import (
    BaseMemberWebhookPayload,
    MemberWebhookPayload,
    WebhookAcceptedResponse,
)
from funda_app.schemas.whatsapp import (
    WhatsAppTemplateSendRequest,
    whatsapp_template_name_for_event,
)
from funda_app.core import normalize_phone_number
from funda_app.services.attio import sync_attio_member
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
    dispatch_keyai_attio_sync(payload)
    dispatch_keyai_whatsapp_message(payload)


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
