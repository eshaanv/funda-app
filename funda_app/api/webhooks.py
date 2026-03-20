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
        "Received Key.ai webhook",
        extra={
            "event": payload.event,
            "member_id": payload.member.id,
            "event_id": payload.eventId,
            "community_id": payload.community.id,
        },
    )
    background_tasks.add_task(
        webhook_service.dispatch_keyai_member_tasks,
        payload,
    )
    logger.info(
        "Queued member background tasks",
        extra={
            "member_id": payload.member.id,
            "event": payload.event,
            "event_id": payload.eventId,
            "status_old": payload.status.old,
            "status_new": payload.status.new,
        },
    )
    response = webhook_service.handle_keyai_webhook(payload=payload)
    logger.info(
        "Accepted Key.ai webhook",
        extra={
            "event": response.event,
            "member_id": response.user_id,
            "event_id": payload.eventId,
            "status": response.status,
        },
    )
    return response
