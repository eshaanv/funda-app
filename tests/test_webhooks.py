import pytest
from fastapi.testclient import TestClient

from funda_app.api import webhooks as webhooks_api
from funda_app.schemas.webhooks import WebhookAcceptedResponse, WhatsAppDispatchResult
from funda_app.services import keyai_webhooks


def test_users_webhook_accepts_json_payload(client: TestClient) -> None:
    response = client.post("/webhooks/keyai/users", json={"name": "Ada"})

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "keyai.users",
        "user_id": None,
    }


def test_users_webhook_accepts_array_payload(client: TestClient) -> None:
    response = client.post("/webhooks/keyai/users", json=["raw", "payload"])

    assert response.status_code == 202
    assert response.json()["event"] == "keyai.users"


def test_user_status_webhook_calls_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_handler(user_id: str, payload: object) -> WebhookAcceptedResponse:
        captured["user_id"] = user_id
        captured["payload"] = payload
        return WebhookAcceptedResponse(event="keyai.user_status", user_id=user_id)

    monkeypatch.setattr(
        webhooks_api.webhook_service, "handle_user_status_webhook", fake_handler
    )

    response = client.post(
        "/webhooks/keyai/users/user-123/status",
        json={"status": "approved"},
    )

    assert response.status_code == 202
    assert captured == {
        "user_id": "user-123",
        "payload": {"status": "approved"},
    }
    assert response.json() == {
        "status": "accepted",
        "event": "keyai.user_status",
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

    response = keyai_webhooks.handle_user_status_webhook(
        user_id="user-456",
        payload={"status": "approved"},
    )

    event = captured["event"]

    assert isinstance(event, keyai_webhooks.KeyAIWebhookEvent)
    assert event.event == "keyai.user_status"
    assert event.user_id == "user-456"
    assert event.payload == {"status": "approved"}
    assert response == WebhookAcceptedResponse(
        event="keyai.user_status",
        user_id="user-456",
    )
