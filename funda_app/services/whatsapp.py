from funda_app.schemas.webhooks import KeyAIWebhookEvent, WhatsAppDispatchResult


def send_keyai_whatsapp_message(event: KeyAIWebhookEvent) -> WhatsAppDispatchResult:
    """
    Builds a placeholder WhatsApp dispatch result for a Key.ai webhook event.

    Args:
        event (KeyAIWebhookEvent): The normalized webhook event being processed.

    Returns:
        WhatsAppDispatchResult: The placeholder delivery status.
    """
    return WhatsAppDispatchResult(
        detail=f"WhatsApp delivery is not configured for {event.event}.",
    )
