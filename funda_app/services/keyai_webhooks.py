import logging

from funda_app.schemas.webhooks import (
    BaseMemberWebhookPayload,
    MemberWebhookPayload,
    MemberWebhookEvent,
    WebhookAcceptedResponse,
)
from funda_app.schemas.whatsapp import (
    WhatsAppDispatchResult,
    WhatsAppTemplateName,
    WhatsAppTemplateSendRequest,
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
