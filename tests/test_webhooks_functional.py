import os

import httpx
import pytest

LOCAL_WEBHOOK_BASE_URL = os.environ.get(
    "LOCAL_WEBHOOK_BASE_URL",
    "http://127.0.0.1:8000",
)


def _local_webhook_test_enabled() -> bool:
    return os.environ.get("RUN_LOCAL_WEBHOOK_TESTS") == "1"


@pytest.mark.skipif(
    not _local_webhook_test_enabled(),
    reason="Set RUN_LOCAL_WEBHOOK_TESTS=1 to run the local FastAPI webhook functional test.",
)
def test_member_joined_local_fastapi_webhook() -> None:
    try:
        response = httpx.post(
            f"{LOCAL_WEBHOOK_BASE_URL}/webhooks/keyai/users",
            json={
                "event": "member.joined",
                "member": {
                    "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
                    "email": "rohan+1@key.ai",
                    "phone": "9256400611",
                    "fullName": "Eshaan Vipani",
                    "lastName": "Vipani",
                    "firstName": "Eshaan",
                    "companyName": None,
                    "linkedinUrl": "https://www.linkedin.com/in/eshaan-vipani/",
                    "companyStage": None,
                },
                "status": {
                    "new": "PENDING",
                    "old": None,
                },
                "eventId": "08964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
                "version": 1,
                "community": {
                    "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
                    "name": "funda",
                },
                "questions": [
                    {
                        "answer": "https://www.linkedin.com/in/eshaan-vipani/",
                        "question": "What is your linked-in url?",
                    },
                    {
                        "answer": "Example Corp",
                        "question": "What is your company name?",
                    },
                    {
                        "answer": "Seed",
                        "question": "What is the funding stage?",
                    },
                ],
                "occurredAt": "2026-03-13T15:05:32.436Z",
            },
            timeout=10.0,
        )
    except httpx.ConnectError as exc:
        pytest.fail(
            f"Could not connect to local FastAPI server at {LOCAL_WEBHOOK_BASE_URL}: {exc}"
        )

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.joined",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }
