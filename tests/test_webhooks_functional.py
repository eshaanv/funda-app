import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from google.cloud import firestore

from funda_app.services.idempotency import KEYAI_WEBHOOK_COLLECTION

# Base URL env vars per target. Override with env to point at different instances.
LOCAL_WEBHOOK_BASE_URL = os.environ.get(
    "LOCAL_WEBHOOK_BASE_URL",
    "http://127.0.0.1:8000",
)
DEV_WEBHOOK_BASE_URL = os.environ.get(
    "DEV_WEBHOOK_BASE_URL",
    "https://funda-app-223110395358.us-central1.run.app",
)
PROD_WEBHOOK_BASE_URL = os.environ.get(
    "PROD_WEBHOOK_BASE_URL",
    "https://funda-app-333824692455.us-central1.run.app",
)

# Optional: set to "local" | "dev" | "prod" to run only that target. Otherwise all
# configured targets run.
WEBHOOK_TEST_TARGET = os.environ.get("WEBHOOK_TEST_TARGET")

WEBHOOK_TARGETS = ["local", "dev", "prod"]
LOCAL_FIRESTORE_PROJECT_ID = os.environ.get(
    "LOCAL_FIRESTORE_PROJECT_ID",
    os.environ.get("GOOGLE_CLOUD_PROJECT"),
)
DEV_FIRESTORE_PROJECT_ID = os.environ.get("DEV_FIRESTORE_PROJECT_ID")
PROD_FIRESTORE_PROJECT_ID = os.environ.get("PROD_FIRESTORE_PROJECT_ID")


def _webhook_test_enabled() -> bool:
    """Functional webhook tests run when RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET is set."""
    return (
        os.environ.get("RUN_LOCAL_WEBHOOK_TESTS") == "1"
        or WEBHOOK_TEST_TARGET in WEBHOOK_TARGETS
    )


def _base_url_for_target(target: str) -> str | None:
    """Returns the webhook base URL for the given target, or None if not configured."""
    if target == "local":
        return LOCAL_WEBHOOK_BASE_URL.rstrip("/")
    if target == "dev":
        return DEV_WEBHOOK_BASE_URL.rstrip("/") if DEV_WEBHOOK_BASE_URL else None
    if target == "prod":
        return PROD_WEBHOOK_BASE_URL.rstrip("/") if PROD_WEBHOOK_BASE_URL else None
    return None


def _firestore_project_id_for_target(target: str) -> str | None:
    """Returns the Firestore project ID for the given target, or None if not configured."""
    if target == "local":
        return LOCAL_FIRESTORE_PROJECT_ID
    if target == "dev":
        return DEV_FIRESTORE_PROJECT_ID
    if target == "prod":
        return PROD_FIRESTORE_PROJECT_ID
    return None


def _common_member() -> dict:
    return {
        "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
        "email": "eshaanvipani1@gmail.com",
        "phone": "9256400611",
        "fullName": "Eshaan Vipani",
        "lastName": "Vipani",
        "firstName": "Eshaan",
    }


def _joined_member() -> dict:
    return {
        **_common_member(),
        "companyName": "Wells Fargo",
        "linkedinUrl": "https://www.linkedin.com/in/eshaan-vipani/",
        "companyStage": "Public Company",
    }


def _common_community() -> dict:
    return {
        "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
        "name": "funda",
    }


def _post_webhook(json: dict, base_url: str) -> httpx.Response:
    try:
        return httpx.post(
            f"{base_url}/webhooks/keyai/users",
            json=json,
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        pytest.fail(
            f"Could not connect to webhook at {base_url}: {exc}"
        )


def _build_joined_payload(event_id: str) -> dict[str, object]:
    return {
        "event": "member.joined",
        "member": _joined_member(),
        "status": {"new": "PENDING", "old": None},
        "eventId": event_id,
        "version": 1,
        "community": _common_community(),
        "questions": [
            {"question": "Linkedin URL?", "answer": "linkedin.com/in/eshaan-vipani/"},
            {
                "question": "WhatsApp Phone Number? (Needed to add you into our WhatsApp community)",
                "answer": "9256400611",
            },
            {"question": "Company Name?", "answer": "Wells Fargo"},
            {
                "question": "Company Website Domain? (e.g. www.newco.com)",
                "answer": "https://www.wellsfargo.com/",
            },
            {"question": "Job Title?", "answer": "Software Engineer"},
            {"question": "Funding Stage?", "answer": "Prefer not to say"},
            {"question": "What describes you best?", "answer": "Service Provider"},
        ],
        "occurredAt": "2026-03-13T15:05:32.436Z",
    }


def _build_approved_payload(event_id: str) -> dict[str, object]:
    return {
        "event": "member.approved",
        "member": _common_member(),
        "status": {"old": "PENDING", "new": "APPROVED"},
        "eventId": event_id,
        "version": 1,
        "community": _common_community(),
        "occurredAt": "2026-03-13T15:06:00.000Z",
    }


def _should_skip_target(target: str) -> tuple[bool, str]:
    """Returns (skip, reason). Skip when opt-in missing, target filtered, or URL not set."""
    if not _webhook_test_enabled():
        return True, "Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run."
    if WEBHOOK_TEST_TARGET is not None and target != WEBHOOK_TEST_TARGET:
        return True, f"WEBHOOK_TEST_TARGET={WEBHOOK_TEST_TARGET!r}, skipping {target!r}."
    base_url = _base_url_for_target(target)
    if base_url is None:
        return True, f"No base URL for {target!r}. Set {'DEV_WEBHOOK_BASE_URL' if target == 'dev' else 'PROD_WEBHOOK_BASE_URL'}."
    return False, ""


def _should_skip_firestore_target(target: str) -> tuple[bool, str]:
    """Returns (skip, reason) for Firestore-backed webhook functional tests."""
    skip, reason = _should_skip_target(target)
    if skip:
        return skip, reason
    if _firestore_project_id_for_target(target) is None:
        return True, (
            f"No Firestore project ID for {target!r}. "
            f"Set {'LOCAL_FIRESTORE_PROJECT_ID or GOOGLE_CLOUD_PROJECT' if target == 'local' else 'DEV_FIRESTORE_PROJECT_ID' if target == 'dev' else 'PROD_FIRESTORE_PROJECT_ID'}."
        )
    return False, ""


def _wait_for_firestore_event_document(
    target: str,
    event_id: str,
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    """Polls Firestore until the idempotency document for the event appears."""
    project_id = _firestore_project_id_for_target(target)
    if project_id is None:
        pytest.fail(f"Missing Firestore project ID for target {target!r}")

    client = firestore.Client(project=project_id)
    document_ref = client.collection(KEYAI_WEBHOOK_COLLECTION).document(event_id)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        snapshot = document_ref.get()
        if snapshot.exists:
            data = snapshot.to_dict()
            if data is None:
                pytest.fail(f"Firestore document {event_id!r} exists but has no data")
            return data
        time.sleep(0.5)

    pytest.fail(
        f"Timed out waiting for Firestore document {KEYAI_WEBHOOK_COLLECTION}/{event_id} "
        f"in project {project_id}"
    )


def _wait_for_firestore_event_fields(
    target: str,
    event_id: str,
    expected_fields: dict[str, object],
    timeout_seconds: float = 40.0,
) -> dict[str, object]:
    """Polls Firestore until the event document contains the expected field values."""
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        document = _wait_for_firestore_event_document(
            target=target,
            event_id=event_id,
            timeout_seconds=2.0,
        )
        if all(document.get(key) == value for key, value in expected_fields.items()):
            return document
        time.sleep(0.5)

    pytest.fail(
        f"Timed out waiting for Firestore document {KEYAI_WEBHOOK_COLLECTION}/{event_id} "
        f"to match {expected_fields!r}"
    )


def _delete_firestore_event_document(target: str, event_id: str) -> None:
    """Deletes a Firestore idempotency document when present."""
    project_id = _firestore_project_id_for_target(target)
    if project_id is None:
        pytest.fail(f"Missing Firestore project ID for target {target!r}")

    firestore.Client(project=project_id).collection(KEYAI_WEBHOOK_COLLECTION).document(
        event_id
    ).delete()


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_joined_webhook(target: str) -> None:
    skip, reason = _should_skip_target(target)
    if skip:
        pytest.skip(reason)
    base_url = _base_url_for_target(target)
    payload = _build_joined_payload(str(uuid4()))
    response = _post_webhook(payload, base_url)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.joined",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_approved_webhook(target: str) -> None:
    skip, reason = _should_skip_target(target)
    if skip:
        pytest.skip(reason)
    base_url = _base_url_for_target(target)
    payload = _build_approved_payload(str(uuid4()))
    response = _post_webhook(payload, base_url)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.approved",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_rejected_webhook(target: str) -> None:
    skip, reason = _should_skip_target(target)
    if skip:
        pytest.skip(reason)
    base_url = _base_url_for_target(target)
    payload = {
        "event": "member.rejected",
        "member": _common_member(),
        "status": {"old": "PENDING", "new": "REJECTED"},
        "eventId": str(uuid4()),
        "version": 1,
        "community": _common_community(),
        "occurredAt": "2026-03-13T15:07:00.000Z",
    }
    response = _post_webhook(payload, base_url)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.rejected",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_removed_webhook(target: str) -> None:
    skip, reason = _should_skip_target(target)
    if skip:
        pytest.skip(reason)
    base_url = _base_url_for_target(target)
    payload = {
        "event": "member.removed",
        "member": _common_member(),
        "status": {"old": "APPROVED", "new": "REMOVED"},
        "eventId": str(uuid4()),
        "version": 1,
        "community": _common_community(),
        "occurredAt": "2026-03-13T15:08:00.000Z",
    }
    response = _post_webhook(payload, base_url)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.removed",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_left_webhook(target: str) -> None:
    skip, reason = _should_skip_target(target)
    if skip:
        pytest.skip(reason)
    base_url = _base_url_for_target(target)
    payload = {
        "event": "member.left",
        "member": _common_member(),
        "status": {"old": "APPROVED", "new": "LEFT"},
        "eventId": str(uuid4()),
        "version": 1,
        "community": _common_community(),
        "occurredAt": "2026-03-13T15:09:00.000Z",
    }
    response = _post_webhook(payload, base_url)
    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.left",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


@pytest.mark.parametrize("target", ["local"])
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_joined_webhook_dedupes_concurrent_duplicate_event_ids(
    target: str,
) -> None:
    skip, reason = _should_skip_firestore_target(target)
    if skip:
        pytest.skip(reason)

    base_url = _base_url_for_target(target)
    event_id = str(uuid4())
    payload = _build_joined_payload(event_id)

    _delete_firestore_event_document(target=target, event_id=event_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_post_webhook, payload, base_url),
            executor.submit(_post_webhook, payload, base_url),
        ]
        responses = [future.result() for future in futures]

    assert [response.status_code for response in responses] == [202, 202]

    document = _wait_for_firestore_event_document(target=target, event_id=event_id)
    assert document["event_id"] == event_id
    assert document["member_id"] == "14b8d602-1eee-11f1-b904-0242ac14000a"
    assert document["event_type"] == "member.joined"
    assert document["status"] in {"processing", "completed", "failed"}


@pytest.mark.parametrize("target", WEBHOOK_TARGETS)
@pytest.mark.skipif(
    not _webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 or WEBHOOK_TEST_TARGET=local|dev|prod to run.",
)
def test_member_approved_webhook_completes_admin_notification(
    target: str,
) -> None:
    skip, reason = _should_skip_firestore_target(target)
    if skip:
        pytest.skip(reason)

    base_url = _base_url_for_target(target)
    event_id = str(uuid4())
    payload = _build_approved_payload(event_id)

    _delete_firestore_event_document(target=target, event_id=event_id)

    response = _post_webhook(payload, base_url)

    assert response.status_code == 202

    document = _wait_for_firestore_event_fields(
        target=target,
        event_id=event_id,
        expected_fields={
            "event_id": event_id,
            "event_type": "member.approved",
            "attio_done": True,
            "whatsapp_done": True,
            "admin_notification_done": True,
            "status": "completed",
        },
    )
    assert document["member_id"] == "14b8d602-1eee-11f1-b904-0242ac14000a"
