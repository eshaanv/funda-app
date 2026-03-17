import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from funda_app.api import webhooks as webhooks_api
from funda_app.schemas.whatsapp import WhatsAppDispatchResult, WhatsAppTemplateName
from funda_app.schemas.webhooks import (
    BaseMemberWebhookPayload,
    MemberApprovedWebhookPayload,
    MemberJoinedWebhookPayload,
    MemberRejectedWebhookPayload,
    MemberWebhookEvent,
    WebhookAcceptedResponse,
)
from funda_app.services import keyai_webhooks


def _build_joined_payload() -> dict[str, object]:
    return {
        "event": "member.joined",
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
            },
            {
                "answer": "https://www.linkedin.com/in/rohan-jain",
                "question": "What is your linked-in url?",
            },
            {
                "answer": "Acme AI",
                "question": "What is your company name?",
            },
            {
                "answer": "Seed",
                "question": "What is the funding stage?",
            },
        ],
        "occurredAt": "2026-03-13T15:05:32.436Z",
    }


def _build_approved_payload() -> dict[str, object]:
    return {
        "event": "member.approved",
        "member": {
            "id": "user-456",
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
            "new": "APPROVED",
            "old": "PENDING",
        },
        "eventId": "08964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
        "version": 1,
        "community": {
            "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
            "name": "funda",
        },
        "occurredAt": "2026-03-13T15:05:32.436Z",
    }


def _build_rejected_payload() -> dict[str, object]:
    payload = _build_approved_payload()
    payload["event"] = "member.rejected"
    payload["status"] = {
        "new": "REJECTED",
        "old": "PENDING",
    }
    return payload


def test_users_webhook_accepts_json_payload(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _build_joined_payload()

    monkeypatch.setattr(
        webhooks_api.webhook_service,
        "dispatch_keyai_member_tasks",
        lambda webhook_payload: None,
    )

    response = client.post("/webhooks/keyai/users", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "event": "member.joined",
        "user_id": "14b8d602-1eee-11f1-b904-0242ac14000a",
    }


def test_users_webhook_rejects_array_payload(client: TestClient) -> None:
    response = client.post("/webhooks/keyai/users", json=["raw", "payload"])

    assert response.status_code == 422


def test_keyai_webhook_calls_service(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_handler(payload: BaseMemberWebhookPayload) -> WebhookAcceptedResponse:
        captured["payload"] = payload
        return WebhookAcceptedResponse(
            event=MemberWebhookEvent.MEMBER_JOINED,
            user_id="user-123",
        )

    monkeypatch.setattr(
        webhooks_api.webhook_service, "handle_keyai_webhook", fake_handler
    )
    monkeypatch.setattr(
        webhooks_api.webhook_service,
        "dispatch_keyai_member_tasks",
        lambda webhook_payload: None,
    )

    response = client.post("/webhooks/keyai/users", json=_build_joined_payload())

    assert response.status_code == 202
    payload = captured["payload"]
    assert isinstance(payload, MemberJoinedWebhookPayload)
    assert payload.event == MemberWebhookEvent.MEMBER_JOINED
    assert payload.member.id == "14b8d602-1eee-11f1-b904-0242ac14000a"
    assert response.json() == {
        "status": "accepted",
        "event": "member.joined",
        "user_id": "user-123",
    }


def test_users_webhook_schedules_background_tasks_for_joined_event(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_dispatch(payload: BaseMemberWebhookPayload) -> None:
        captured["payload"] = payload

    monkeypatch.setattr(
        webhooks_api.webhook_service,
        "dispatch_keyai_member_tasks",
        fake_dispatch,
    )

    response = client.post("/webhooks/keyai/users", json=_build_joined_payload())

    assert response.status_code == 202
    payload = captured["payload"]
    assert isinstance(payload, MemberJoinedWebhookPayload)
    assert payload.member.id == "14b8d602-1eee-11f1-b904-0242ac14000a"


def test_users_webhook_schedules_background_tasks_for_non_joined_event(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_dispatch(payload: BaseMemberWebhookPayload) -> None:
        captured["payload"] = payload

    monkeypatch.setattr(
        webhooks_api.webhook_service,
        "dispatch_keyai_member_tasks",
        fake_dispatch,
    )

    response = client.post("/webhooks/keyai/users", json=_build_approved_payload())

    assert response.status_code == 202
    payload = captured["payload"]
    assert isinstance(payload, MemberApprovedWebhookPayload)
    assert payload.event == MemberWebhookEvent.MEMBER_APPROVED


def test_users_webhook_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/webhooks/keyai/users",
        content='{"broken":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_users_webhook_rejects_joined_payload_without_questions(
    client: TestClient,
) -> None:
    payload = _build_joined_payload()
    payload.pop("questions")

    response = client.post("/webhooks/keyai/users", json=payload)

    assert response.status_code == 422


def test_service_builds_joined_whatsapp_request() -> None:
    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
    )

    assert send_request is not None
    assert send_request.to == "8511152215"
    assert send_request.template_name == WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION
    assert send_request.template_metadata == {"first_name": "Rohan"}


def test_service_builds_approved_admin_notification_request() -> None:
    send_request = keyai_webhooks.build_new_member_admin_notification_request(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
        settings=type("Settings", (), {"new_member_admin_phone": "15551234567"})(),
    )

    assert send_request is not None
    assert send_request.to == "15551234567"
    assert (
        send_request.template_name
        == WhatsAppTemplateName.FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION
    )
    assert send_request.template_metadata == {"full_name": "Rohan Jain"}


def test_service_skips_non_approved_admin_notification_request() -> None:
    send_request = keyai_webhooks.build_new_member_admin_notification_request(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
        settings=type("Settings", (), {"new_member_admin_phone": "15551234567"})(),
    )

    assert send_request is None


def test_service_builds_attio_sync_request_with_question_fallbacks() -> None:
    sync_request = keyai_webhooks.build_keyai_attio_sync_request(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
    )

    assert sync_request.event == MemberWebhookEvent.MEMBER_JOINED
    assert sync_request.member_status.value == "PENDING"
    assert sync_request.person.keyai_member_id == "14b8d602-1eee-11f1-b904-0242ac14000a"
    assert sync_request.person.email == "rohan+1@key.ai"
    assert sync_request.person.phone == "+18511152215"
    assert sync_request.person.linkedin_url == "https://www.linkedin.com/in/rohan-jain"
    assert sync_request.company is not None
    assert sync_request.company.name == "Acme AI"
    assert sync_request.company.stage == "Seed"
    assert sync_request.person.job_title is None
    assert sync_request.company.company_website is None


def test_service_builds_attio_sync_request_with_job_title_and_company_website() -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"].extend(
        [
            {"question": "What is your job title?", "answer": "CEO"},
            {"question": "What is your company website domain?", "answer": "acme.ai"},
        ]
    )
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.person.job_title == "CEO"
    assert sync_request.company is not None
    assert sync_request.company.company_website == "acme.ai"


@pytest.mark.parametrize(
    ("payload", "expected_template_name"),
    [
        (
            MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
            WhatsAppTemplateName.FUNDA_MEMBERSHIP_APPROVED,
        ),
        (
            MemberRejectedWebhookPayload.model_validate(_build_rejected_payload()),
            WhatsAppTemplateName.FUNDA_MEMBERSHIP_REJECTED,
        ),
    ],
)
def test_service_builds_non_joined_whatsapp_dispatch_request(
    payload: BaseMemberWebhookPayload,
    expected_template_name: WhatsAppTemplateName,
) -> None:
    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload=payload)

    assert send_request is not None
    assert send_request.to == "8511152215"
    assert send_request.template_name == expected_template_name
    assert send_request.template_metadata == {"first_name": "Rohan"}


def test_service_dispatches_joined_event_to_whatsapp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sender(send_request) -> WhatsAppDispatchResult:
        captured["send_request"] = send_request
        return WhatsAppDispatchResult(
            status="sent",
            detail="accepted",
            message_id="wamid.123",
        )

    monkeypatch.setattr(keyai_webhooks, "send_whatsapp_template_message", fake_sender)

    keyai_webhooks.dispatch_keyai_whatsapp_message(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
    )

    send_request = captured["send_request"]

    assert send_request.template_name == WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION
    assert send_request.template_metadata == {"first_name": "Rohan"}


@pytest.mark.parametrize(
    ("payload", "expected_template_name"),
    [
        (
            MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
            WhatsAppTemplateName.FUNDA_MEMBERSHIP_APPROVED,
        ),
        (
            MemberRejectedWebhookPayload.model_validate(_build_rejected_payload()),
            WhatsAppTemplateName.FUNDA_MEMBERSHIP_REJECTED,
        ),
    ],
)
def test_service_dispatches_non_joined_event_to_whatsapp(
    payload: BaseMemberWebhookPayload,
    expected_template_name: WhatsAppTemplateName,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sender(send_request) -> WhatsAppDispatchResult:
        captured["send_request"] = send_request
        return WhatsAppDispatchResult(
            status="sent",
            detail="accepted",
            message_id="wamid.123",
        )

    monkeypatch.setattr(keyai_webhooks, "send_whatsapp_template_message", fake_sender)

    keyai_webhooks.dispatch_keyai_whatsapp_message(payload=payload)

    send_request = captured["send_request"]

    assert send_request.template_name == expected_template_name
    assert send_request.template_metadata == {"first_name": "Rohan"}


def test_service_dispatches_approved_event_to_admin_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sender(send_request) -> WhatsAppDispatchResult:
        captured["send_request"] = send_request
        return WhatsAppDispatchResult(
            status="sent",
            detail="accepted",
            message_id="wamid.456",
        )

    monkeypatch.setattr(keyai_webhooks, "send_whatsapp_template_message", fake_sender)
    monkeypatch.setattr(
        keyai_webhooks,
        "get_app_settings",
        lambda: type("Settings", (), {"new_member_admin_phone": "15551234567"})(),
    )

    keyai_webhooks.dispatch_new_member_admin_notification(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
    )

    send_request = captured["send_request"]

    assert send_request.to == "15551234567"
    assert (
        send_request.template_name
        == WhatsAppTemplateName.FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION
    )
    assert send_request.template_metadata == {"full_name": "Rohan Jain"}


def test_service_dispatches_member_event_to_attio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_sync(sync_request):
        captured["sync_request"] = sync_request
        return type(
            "FakeAttioResult",
            (),
            {
                "person_record_id": "person-123",
                "company_record_id": "company-123",
                "lifecycle_entry_id": "entry-123",
            },
        )()

    monkeypatch.setattr(keyai_webhooks, "sync_attio_member", fake_sync)

    keyai_webhooks.dispatch_keyai_attio_sync(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
    )

    sync_request = captured["sync_request"]

    assert sync_request.person.keyai_member_id == "14b8d602-1eee-11f1-b904-0242ac14000a"
    assert sync_request.person.phone == "+18511152215"
    assert sync_request.company is not None
    assert sync_request.company.name == "Acme AI"


def test_joined_webhook_model_requires_questions() -> None:
    payload = _build_joined_payload()
    payload.pop("questions")

    with pytest.raises(ValidationError):
        MemberJoinedWebhookPayload.model_validate(payload)


def test_approved_webhook_model_rejects_invalid_status_transition() -> None:
    payload = _build_approved_payload()
    payload["status"] = {"old": "APPROVED", "new": "APPROVED"}

    with pytest.raises(ValidationError):
        MemberApprovedWebhookPayload.model_validate(payload)
