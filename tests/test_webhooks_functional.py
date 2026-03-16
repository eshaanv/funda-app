import os

import httpx
import pytest

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


def _common_member() -> dict:
    return {
        "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
        "email": "eshaanvipani1@gmail.com",
        "phone": "9256400611",
        "fullName": "Eshaan Vipani",
        "lastName": "Vipani",
        "firstName": "Eshaan",
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
    payload = {
        "event": "member.joined",
        "member": _common_member(),
        "status": {"new": "PENDING", "old": None},
        "eventId": "08964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
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
    payload = {
        "event": "member.approved",
        "member": _common_member(),
        "status": {"old": "PENDING", "new": "APPROVED"},
        "eventId": "18964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
        "version": 1,
        "community": _common_community(),
        "occurredAt": "2026-03-13T15:06:00.000Z",
    }
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
        "eventId": "28964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
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
        "eventId": "38964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
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
        "eventId": "48964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
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
