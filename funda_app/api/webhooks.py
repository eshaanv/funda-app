from fastapi import APIRouter, Body, Path, status

from funda_app.schemas.webhooks import JSONValue, WebhookAcceptedResponse
from funda_app.services import keyai_webhooks as webhook_service

router = APIRouter(prefix="/webhooks/keyai", tags=["webhooks"])


@router.post(
    "/users",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_users_webhook(
    payload: JSONValue = Body(..., description="Raw JSON payload sent by Key.ai."),
) -> WebhookAcceptedResponse:
    return webhook_service.handle_users_webhook(payload=payload)


@router.post(
    "/users/{user_id}/status",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_user_status_webhook(
    user_id: str = Path(..., description="The Key.ai user identifier."),
    payload: JSONValue = Body(..., description="Raw JSON payload sent by Key.ai."),
) -> WebhookAcceptedResponse:
    return webhook_service.handle_user_status_webhook(user_id=user_id, payload=payload)
