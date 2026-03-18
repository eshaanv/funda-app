from datetime import UTC, datetime

from google.cloud import firestore
from pydantic import ValidationError

from funda_app.app_settings import get_app_settings
from funda_app.schemas.idempotency import (
    KeyAIEventProcessingState,
    KeyAIEventRecord,
)

KEYAI_WEBHOOK_COLLECTION = "keyai_webhook_events"


def begin_keyai_event_processing(
    event_id: str,
    member_id: str,
    event_type: str,
) -> KeyAIEventProcessingState:
    """
    Claims or resumes processing for a Key.ai webhook event.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
        member_id (str): Key.ai member ID.
        event_type (str): Key.ai event name.

    Returns:
        KeyAIEventProcessingState: Whether processing should continue and which
            side effects already completed.
    """
    client = get_app_settings().firestore_client_settings.client
    transaction = client.transaction()
    document_ref = client.collection(KEYAI_WEBHOOK_COLLECTION).document(event_id)
    return _begin_keyai_event_processing(
        transaction=transaction,
        document_ref=document_ref,
        event_id=event_id,
        member_id=member_id,
        event_type=event_type,
    )


@firestore.transactional
def _begin_keyai_event_processing(
    transaction: firestore.Transaction,
    document_ref: firestore.DocumentReference,
    event_id: str,
    member_id: str,
    event_type: str,
) -> KeyAIEventProcessingState:
    snapshot = document_ref.get(transaction=transaction)
    now = datetime.now(UTC)

    if not snapshot.exists:
        record = KeyAIEventRecord(
            event_id=event_id,
            member_id=member_id,
            event_type=event_type,
            status="processing",
        )
        transaction.create(
            document_ref,
            {
                **record.model_dump(),
                "created_at": now,
                "updated_at": now,
            },
        )
        return KeyAIEventProcessingState(should_process=True)

    data = snapshot.to_dict() or {}
    try:
        record = KeyAIEventRecord.model_validate(data)
    except ValidationError:
        transaction.set(
            document_ref,
            {
                "event_id": event_id,
                "member_id": member_id,
                "event_type": event_type,
                "status": "processing",
                "attio_done": False,
                "whatsapp_done": False,
                "admin_notification_done": False,
                "updated_at": now,
            },
            merge=True,
        )
        return KeyAIEventProcessingState(should_process=True)

    if record.status == "completed":
        return KeyAIEventProcessingState(
            should_process=False,
            attio_done=record.attio_done,
            whatsapp_done=record.whatsapp_done,
            admin_notification_done=record.admin_notification_done,
        )

    if record.status == "processing":
        return KeyAIEventProcessingState(
            should_process=False,
            attio_done=record.attio_done,
            whatsapp_done=record.whatsapp_done,
            admin_notification_done=record.admin_notification_done,
        )

    transaction.update(
        document_ref,
        {
            "status": "processing",
            "updated_at": now,
        },
    )
    return KeyAIEventProcessingState(
        should_process=True,
        attio_done=record.attio_done,
        whatsapp_done=record.whatsapp_done,
        admin_notification_done=record.admin_notification_done,
    )


def mark_keyai_event_attio_done(event_id: str) -> None:
    """
    Marks Attio sync as completed for a Key.ai webhook event.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
    """
    _update_keyai_event(
        event_id=event_id,
        data={
            "attio_done": True,
            "updated_at": datetime.now(UTC),
        },
    )


def mark_keyai_event_whatsapp_done(event_id: str) -> None:
    """
    Marks WhatsApp dispatch as completed for a Key.ai webhook event.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
    """
    _update_keyai_event(
        event_id=event_id,
        data={
            "whatsapp_done": True,
            "updated_at": datetime.now(UTC),
        },
    )


def mark_keyai_event_completed(event_id: str) -> None:
    """
    Marks a Key.ai webhook event as completed.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
    """
    _update_keyai_event(
        event_id=event_id,
        data={
            "status": "completed",
            "updated_at": datetime.now(UTC),
        },
    )


def mark_keyai_event_admin_notification_done(event_id: str) -> None:
    """
    Marks the approved-member admin notification as completed.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
    """
    _update_keyai_event(
        event_id=event_id,
        data={
            "admin_notification_done": True,
            "updated_at": datetime.now(UTC),
        },
    )


def mark_keyai_event_failed(event_id: str, error_message: str) -> None:
    """
    Marks a Key.ai webhook event as failed.

    Args:
        event_id (str): Unique Key.ai webhook event ID.
        error_message (str): Failure message for debugging and resume decisions.
    """
    _update_keyai_event(
        event_id=event_id,
        data={
            "status": "failed",
            "last_error": error_message,
            "updated_at": datetime.now(UTC),
        },
    )


def _update_keyai_event(event_id: str, data: dict[str, object]) -> None:
    get_app_settings().firestore_client_settings.client.collection(
        KEYAI_WEBHOOK_COLLECTION
    ).document(
        event_id
    ).set(data, merge=True)
