import logging

from fastapi import APIRouter, BackgroundTasks, Body, status

from funda_app.schemas.webhooks import (
    MemberWebhookPayload,
    WebhookAcceptedResponse,
)
from funda_app.services import keyai_webhooks as webhook_service

router = APIRouter(prefix="/webhooks/keyai", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post(
    "/users",
    response_model=WebhookAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_keyai_webhook(
    background_tasks: BackgroundTasks,
    payload: MemberWebhookPayload = Body(
        ...,
        description="Member webhook payload sent by Key.ai.",
    ),
) -> WebhookAcceptedResponse:
    logger.info(
        "Received Key.ai webhook: event=%s member_id=%s",
        payload.event,
        payload.member.id,
    )
    logger.info(
        "Queued member background tasks: member_id=%s event=%s event_id=%s",
        payload.member.id,
        payload.event,
        payload.eventId,
    )
    background_tasks.add_task(
        webhook_service.dispatch_keyai_member_tasks,
        payload,
    )
    return webhook_service.handle_keyai_webhook(payload=payload)
