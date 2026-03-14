from fastapi import APIRouter, Body, status

from funda_app.schemas.webhooks import JSONValue, WebhookAcceptedResponse
from funda_app.services import keyai_webhooks as webhook_service

router = APIRouter(prefix="/webhooks/keyai", tags=["webhooks"])


@router.post(
    "/users",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_keyai_webhook(
    payload: JSONValue = Body(..., description="Raw JSON payload sent by Key.ai."),
) -> WebhookAcceptedResponse:
    return webhook_service.handle_keyai_webhook(payload=payload)
