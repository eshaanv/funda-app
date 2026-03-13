from funda_app.schemas.webhooks import (
    JSONValue,
    KeyAIWebhookEvent,
    WebhookAcceptedResponse,
)
from funda_app.services.whatsapp import send_keyai_whatsapp_message


def handle_users_webhook(payload: JSONValue) -> WebhookAcceptedResponse:
    """
    Handles webhook payloads received on the Key.ai users endpoint.

    Args:
        payload (JSONValue): The raw JSON payload sent by Key.ai.

    Returns:
        WebhookAcceptedResponse: The acknowledgment returned to the webhook caller.
    """
    event = KeyAIWebhookEvent(event="keyai.users", payload=payload)
    return _process_event(event)


def handle_user_status_webhook(
    user_id: str,
    payload: JSONValue,
) -> WebhookAcceptedResponse:
    """
    Handles webhook payloads received on the Key.ai user status endpoint.

    Args:
        user_id (str): The Key.ai user identifier from the URL path.
        payload (JSONValue): The raw JSON payload sent by Key.ai.

    Returns:
        WebhookAcceptedResponse: The acknowledgment returned to the webhook caller.
    """
    event = KeyAIWebhookEvent(
        event="keyai.user_status", user_id=user_id, payload=payload
    )
    return _process_event(event)


def _process_event(event: KeyAIWebhookEvent) -> WebhookAcceptedResponse:
    send_keyai_whatsapp_message(event)
    return WebhookAcceptedResponse(event=event.event, user_id=event.user_id)
