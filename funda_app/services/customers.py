from datetime import UTC, datetime

from google.cloud import firestore

from funda_app.app_settings import AppSettings, get_app_settings
from funda_app.schemas.crm import ATTIO_SCHEMA
from funda_app.schemas.customers import (
    KeyAICustomerSyncRequest,
    KeyAICustomerSyncResult,
)

KEYAI_CUSTOMERS_COLLECTION = "keyai_customers"


def sync_keyai_customer(
    sync_request: KeyAICustomerSyncRequest,
    settings: AppSettings | None = None,
) -> KeyAICustomerSyncResult:
    """
    Syncs a Key.ai customer latest-state document and event history to Firestore.

    Args:
        sync_request (KeyAICustomerSyncRequest): Normalized customer sync request.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        KeyAICustomerSyncResult: Firestore document IDs written by the sync.
    """
    runtime_settings = settings or get_app_settings()
    client = runtime_settings.firestore_client_settings.client
    customer_ref = client.collection(KEYAI_CUSTOMERS_COLLECTION).document(
        sync_request.person.keyai_member_id
    )
    event_ref = customer_ref.collection("events").document(sync_request.event_id)
    transaction = client.transaction()

    _sync_keyai_customer(
        transaction=transaction,
        customer_ref=customer_ref,
        event_ref=event_ref,
        sync_request=sync_request,
    )

    return KeyAICustomerSyncResult(
        status="synced",
        customer_document_id=sync_request.person.keyai_member_id,
        event_document_id=sync_request.event_id,
    )


@firestore.transactional
def _sync_keyai_customer(
    transaction: firestore.Transaction,
    customer_ref: firestore.DocumentReference,
    event_ref: firestore.DocumentReference,
    sync_request: KeyAICustomerSyncRequest,
) -> None:
    snapshot = customer_ref.get(transaction=transaction)
    now = datetime.now(UTC)
    transaction.set(
        customer_ref,
        _build_customer_document_update(
            sync_request=sync_request,
            document_exists=snapshot.exists,
            synced_at=now,
        ),
        merge=True,
    )
    transaction.set(
        event_ref,
        _build_customer_event_document(
            sync_request=sync_request,
            synced_at=now,
        ),
        merge=True,
    )


def _build_customer_document_update(
    sync_request: KeyAICustomerSyncRequest,
    document_exists: bool,
    synced_at: datetime,
) -> dict[str, object]:
    update: dict[str, object] = {
        "member_id": sync_request.person.keyai_member_id,
        "community_id": sync_request.community_id,
        "community_name": sync_request.community_name,
        "member_status": sync_request.member_status.value,
        "latest_event": sync_request.event.value,
        "latest_event_id": sync_request.event_id,
        "latest_event_at": sync_request.occurred_at,
        "updated_at": synced_at,
        ATTIO_SCHEMA.lifecycle.timestamp_attribute_for_event(
            sync_request.event
        ): sync_request.occurred_at,
    }

    if not document_exists:
        update.update(
            {
                "created_at": synced_at,
                "first_event": sync_request.event.value,
                "first_event_id": sync_request.event_id,
                "first_event_at": sync_request.occurred_at,
            }
        )

    update.update(_non_empty_person_fields(sync_request))
    update.update(_non_empty_company_fields(sync_request))
    if sync_request.question_answers:
        update.update(sync_request.question_answers)
        update["question_answers"] = sync_request.question_answers
    if sync_request.keyai_questions:
        update["keyai_questions"] = sync_request.keyai_questions
    return update


def _build_customer_event_document(
    sync_request: KeyAICustomerSyncRequest,
    synced_at: datetime,
) -> dict[str, object]:
    return {
        "event_id": sync_request.event_id,
        "event_type": sync_request.event.value,
        "member_id": sync_request.person.keyai_member_id,
        "community_id": sync_request.community_id,
        "community_name": sync_request.community_name,
        "old_status": (
            sync_request.previous_status.value
            if sync_request.previous_status is not None
            else None
        ),
        "new_status": sync_request.member_status.value,
        "occurred_at": sync_request.occurred_at,
        "person": _person_snapshot(sync_request),
        "company": _company_snapshot(sync_request),
        "question_answers": sync_request.question_answers,
        "keyai_questions": sync_request.keyai_questions,
        "created_at": synced_at,
    }


def _non_empty_person_fields(
    sync_request: KeyAICustomerSyncRequest,
) -> dict[str, object]:
    person = sync_request.person
    fields: dict[str, object | None] = {
        "email": person.email,
        "full_name": person.full_name,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "phone": person.phone,
        "linkedin_url": person.linkedin_url,
        "job_title": person.job_title,
    }
    return {key: value for key, value in fields.items() if value is not None}


def _non_empty_company_fields(
    sync_request: KeyAICustomerSyncRequest,
) -> dict[str, object]:
    if sync_request.company is None:
        return {}

    company = sync_request.company
    fields: dict[str, object | None] = {
        "company_name": company.name,
        "company_stage": company.stage,
        "company_website": company.company_website,
    }
    return {key: value for key, value in fields.items() if value is not None}


def _person_snapshot(
    sync_request: KeyAICustomerSyncRequest,
) -> dict[str, object | None]:
    person = sync_request.person
    return {
        "member_id": person.keyai_member_id,
        "email": person.email,
        "full_name": person.full_name,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "phone": person.phone,
        "linkedin_url": person.linkedin_url,
        "job_title": person.job_title,
    }


def _company_snapshot(
    sync_request: KeyAICustomerSyncRequest,
) -> dict[str, object | None] | None:
    if sync_request.company is None:
        return None

    company = sync_request.company
    return {
        "name": company.name,
        "stage": company.stage,
        "company_website": company.company_website,
    }
