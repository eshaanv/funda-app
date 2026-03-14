import pytest
from fastapi.testclient import TestClient

from funda_app.api import webhooks as webhooks_api
from funda_app.schemas.webhooks import WebhookAcceptedResponse, WhatsAppDispatchResult
from funda_app.services import keyai_webhooks


def test_users_webhook_accepts_json_payload(client: TestClient) -> None:
    payload = {
        "event": "member.status.changed",
        "member": {
            "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
            "email": "rohan+1@key.ai",
            "phone": "8511152215",
            "fullName": "Rohan Jain",
            "lastName": "Jain",
            "firstName": "Rohan",
            "companyName": None,
            "linkedinUrl": None,
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
                "answer": "RJ",
                "question": "What is your first name?",
            }
        ],
        "occurredAt": "2026-03-13T15:05:32.436Z",
    }

    response = client.post("/webhooks/keyai/users", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.status.changed",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


def test_users_webhook_accepts_array_payload(client: TestClient) -> None:
    response = client.post("/webhooks/keyai/users", json=["raw", "payload"])

    assert response.status_code == 202
    assert response.json()["event"] == "keyai.webhook.received"


def test_keyai_webhook_calls_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_handler(payload: object) -> WebhookAcceptedResponse:
        captured["payload"] = payload
        return WebhookAcceptedResponse(
            event="member.status.changed",
            user_id="user-123",
        )

    monkeypatch.setattr(
        webhooks_api.webhook_service, "handle_keyai_webhook", fake_handler
    )

    response = client.post(
        "/webhooks/keyai/users", json={"event": "member.status.changed"}
    )

    assert response.status_code == 202
    assert captured == {
        "payload": {"event": "member.status.changed"},
    }
    assert response.json() == {
        "status": "accepted",
        "event": "member.status.changed",
        "user_id": "user-123",
    }


def test_users_webhook_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/webhooks/keyai/users",
        content='{"broken":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_service_forwards_event_to_whatsapp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sender(event: keyai_webhooks.KeyAIWebhookEvent) -> WhatsAppDispatchResult:
        captured["event"] = event
        return WhatsAppDispatchResult(detail="placeholder")

    monkeypatch.setattr(keyai_webhooks, "send_keyai_whatsapp_message", fake_sender)

    response = keyai_webhooks.handle_keyai_webhook(
        payload={
            "event": "member.status.changed",
            "member": {"id": "user-456"},
            "status": {"new": "APPROVED", "old": "PENDING"},
        },
    )

    event = captured["event"]

    assert isinstance(event, keyai_webhooks.KeyAIWebhookEvent)
    assert event.event == "member.status.changed"
    assert event.user_id == "user-456"
    assert event.payload == {
        "event": "member.status.changed",
        "member": {"id": "user-456"},
        "status": {"new": "APPROVED", "old": "PENDING"},
    }
    assert response == WebhookAcceptedResponse(
        event="member.status.changed",
        user_id="user-456",
    )


def test_keyai_service_extracts_member_id_from_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sender(event: keyai_webhooks.KeyAIWebhookEvent) -> WhatsAppDispatchResult:
        captured["event"] = event
        return WhatsAppDispatchResult(detail="placeholder")

    monkeypatch.setattr(keyai_webhooks, "send_keyai_whatsapp_message", fake_sender)

    response = keyai_webhooks.handle_keyai_webhook(
        payload={
            "event": "member.status.changed",
            "member": {
                "id": "member-789",
                "email": "rohan+1@key.ai",
            },
            "status": {
                "new": "PENDING",
                "old": None,
            },
        }
    )

    event = captured["event"]

    assert isinstance(event, keyai_webhooks.KeyAIWebhookEvent)
    assert event.event == "member.status.changed"
    assert event.user_id == "member-789"
    assert response == WebhookAcceptedResponse(
        event="member.status.changed",
        user_id="member-789",
    )
