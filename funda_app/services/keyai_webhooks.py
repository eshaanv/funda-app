from funda_app.schemas.webhooks import (
    JSONValue,
    KeyAIWebhookEvent,
    WebhookAcceptedResponse,
)
from funda_app.services.whatsapp import send_keyai_whatsapp_message

DEFAULT_KEYAI_EVENT = "keyai.webhook.received"


def handle_keyai_webhook(payload: JSONValue) -> WebhookAcceptedResponse:
    """
    Handles all webhook payloads received from Key.ai.

    Args:
        payload (JSONValue): The raw JSON payload sent by Key.ai.

    Returns:
        WebhookAcceptedResponse: The acknowledgment returned to the webhook caller.
    """
    event = KeyAIWebhookEvent(
        event=_extract_event_name(payload),
        payload=payload,
        user_id=_extract_member_id(payload),
    )
    return _process_event(event)


def _process_event(event: KeyAIWebhookEvent) -> WebhookAcceptedResponse:
    send_keyai_whatsapp_message(event)
    return WebhookAcceptedResponse(event=event.event, user_id=event.user_id)


def _extract_event_name(payload: JSONValue) -> str:
    """
    Extracts the Key.ai event name from a webhook payload.

    Args:
        payload (JSONValue): Raw webhook payload received from Key.ai.

    Returns:
        str: Event name when present, otherwise a fallback value.
    """
    if not isinstance(payload, dict):
        return DEFAULT_KEYAI_EVENT

    event_name = payload.get("event")
    if not isinstance(event_name, str) or not event_name:
        return DEFAULT_KEYAI_EVENT

    return event_name


def _extract_member_id(payload: JSONValue) -> str | None:
    """
    Extracts a Key.ai member identifier from a webhook payload.

    Args:
        payload (JSONValue): Raw webhook payload received from Key.ai.

    Returns:
        str | None: Member identifier when present, otherwise None.
    """
    if not isinstance(payload, dict):
        return None

    member = payload.get("member")
    if not isinstance(member, dict):
        return None

    member_id = member.get("id")
    if not isinstance(member_id, str) or not member_id:
        return None

    return member_id
