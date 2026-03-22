import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from uuid import uuid4

from funda_app.schemas.crm import AttioMemberContext
from funda_app.api import webhooks as webhooks_api
from funda_app.schemas.idempotency import KeyAIEventProcessingState
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
            "phone": "",
            "fullName": "Rohan Jain",
            "lastName": "Jain",
            "firstName": "Rohan",
            "linkedinUrl": "https://www.linkedin.com/in/member-profile",
        },
        "status": {
            "new": "PENDING",
            "old": None,
        },
        "eventId": str(uuid4()),
        "version": 1,
        "community": {
            "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
            "name": "funda",
        },
        "questions": [
            {
                "answer": "RJ",
                "question": "What is your first name?",
                "semantic_key": "first_name",
            },
            {
                "answer": "https://www.linkedin.com/in/rohan-jain",
                "question": "What is your linked-in url?",
                "semantic_key": "linked_in_url",
            },
            {
                "answer": "8511152215",
                "question": "What is your whatsapp number?",
                "semantic_key": "whatsapp_number",
            },
            {
                "answer": "Acme AI",
                "question": "What is your company name?",
                "semantic_key": "company_name",
            },
            {
                "answer": "Seed",
                "question": "What is the funding stage?",
                "semantic_key": "funding_stage",
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
            "linkedinUrl": "https://www.linkedin.com/in/member-profile",
        },
        "status": {
            "new": "APPROVED",
            "old": "PENDING",
        },
        "eventId": str(uuid4()),
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


def test_users_webhook_accepts_joined_payload_without_questions(
    client: TestClient,
) -> None:
    payload = _build_joined_payload()
    payload.pop("questions")

    response = client.post("/webhooks/keyai/users", json=payload)

    assert response.status_code == 202


def test_service_builds_joined_whatsapp_request() -> None:
    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
    )

    assert send_request is not None
    assert send_request.to == "8511152215"
    assert send_request.template_name == WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION
    assert send_request.template_metadata == {"first_name": "Rohan"}


def test_service_builds_approved_admin_notification_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_invoke_gemini(prompt, config=None):
        return (
            '{"individual_blurb":"Rohan is an approved\\tmember of the Funda community.",'
            '"company_blurb":"Acme AI is the company associated\\nwith this member."}'
        )

    monkeypatch.setattr(
        keyai_webhooks,
        "invoke_gemini",
        fake_invoke_gemini,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            company_name="Acme AI",
        )
    )
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
    assert send_request.template_metadata == {
        "full_name": "Rohan Jain",
        "member_sentence": "Rohan is an approved member of the Funda community.",
        "company_sentence": "Acme AI is the company associated with this member.",
    }


def test_service_skips_non_approved_admin_notification_request() -> None:
    send_request = keyai_webhooks.build_new_member_admin_notification_request(
        payload=MemberJoinedWebhookPayload.model_validate(_build_joined_payload()),
        settings=type("Settings", (), {"new_member_admin_phone": "15551234567"})(),
    )

    assert send_request is None


def test_service_builds_attio_sync_request_from_joined_questions() -> None:
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


def test_service_builds_attio_sync_request_with_job_title() -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"].extend(
        [
            {
                "question": "What is your job title?",
                "answer": "CEO",
                "semantic_key": "job_title",
            },
        ]
    )
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.person.job_title == "CEO"
    assert sync_request.company is not None
    assert sync_request.company.company_website is None


def test_service_skips_company_sync_for_non_joined_event_without_company_questions() -> (
    None
):
    payload_data = _build_approved_payload()
    payload = MemberApprovedWebhookPayload.model_validate(payload_data)

    keyai_webhooks.get_member_context_for_member = lambda member_id, settings=None: None
    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.company is None


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
def test_service_builds_non_joined_whatsapp_dispatch_request_from_attio(
    payload: BaseMemberWebhookPayload,
    expected_template_name: WhatsAppTemplateName,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        keyai_webhooks,
        "get_phone_number_for_member",
        lambda member_id, settings=None: "+18511152215",
    )

    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload=payload)

    assert send_request is not None
    assert send_request.to == "+18511152215"
    assert send_request.template_name == expected_template_name
    assert send_request.template_metadata == {"first_name": "Rohan"}


@pytest.mark.parametrize(
    "payload",
    [
        MemberApprovedWebhookPayload.model_validate(
            {
                **_build_approved_payload(),
                "member": {
                    **_build_approved_payload()["member"],
                    "phone": "",
                },
                "questions": [
                    {
                        "answer": "8511152215",
                        "question": "What is your whatsapp number?",
                        "semantic_key": "whatsapp_number",
                    }
                ],
            }
        ),
        MemberRejectedWebhookPayload.model_validate(
            {
                **_build_rejected_payload(),
                "member": {
                    **_build_rejected_payload()["member"],
                    "phone": "",
                },
                "questions": [
                    {
                        "answer": "8511152215",
                        "question": "What is your whatsapp number?",
                        "semantic_key": "whatsapp_number",
                    }
                ],
            }
        ),
    ],
)
def test_service_skips_non_joined_whatsapp_dispatch_without_attio_phone(
    payload: BaseMemberWebhookPayload,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        keyai_webhooks,
        "get_phone_number_for_member",
        lambda member_id, settings=None: None,
    )

    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload=payload)

    assert send_request is None


def test_service_prefers_question_phone_for_joined_whatsapp_dispatch() -> None:
    payload_data = _build_joined_payload()
    payload_data["member"]["phone"] = "19998887777"
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload=payload)

    assert send_request is not None
    assert send_request.to == "8511152215"


def test_service_ignores_payload_phone_for_non_joined_whatsapp_dispatch() -> None:
    payload_data = _build_approved_payload()
    payload_data["member"]["phone"] = "19998887777"
    payload_data["questions"] = [
        {
            "answer": "8511152215",
            "question": "What is your whatsapp number?",
            "semantic_key": "whatsapp_number",
        }
    ]
    payload = MemberApprovedWebhookPayload.model_validate(payload_data)

    keyai_webhooks.get_phone_number_for_member = lambda member_id, settings=None: (
        "+14155550123"
    )
    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload=payload)

    assert send_request is not None
    assert send_request.to == "+14155550123"


def test_service_builds_attio_sync_request_from_questions_before_member_fields() -> (
    None
):
    payload_data = _build_joined_payload()
    payload_data["member"]["phone"] = "19998887777"
    payload_data["member"]["linkedinUrl"] = (
        "https://www.linkedin.com/in/member-fallback"
    )
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.person.phone == "+18511152215"
    assert sync_request.person.linkedin_url == "https://www.linkedin.com/in/rohan-jain"
    assert sync_request.company is not None
    assert sync_request.company.name == "Acme AI"
    assert sync_request.company.stage == "Seed"


def test_service_builds_attio_sync_request_from_attio_context_for_non_joined_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_data = _build_approved_payload()
    payload_data["member"]["phone"] = "19998887777"
    payload_data["member"]["linkedinUrl"] = "https://www.linkedin.com/in/member-profile"
    payload_data["questions"] = []
    payload = MemberApprovedWebhookPayload.model_validate(payload_data)

    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            phone="+14155550123",
            linkedin_url="https://www.linkedin.com/in/attio-profile",
            job_title="Founder",
            company_name="Attio Company",
            company_stage="Series A",
        )
    )
    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.person.phone == "+14155550123"
    assert sync_request.person.linkedin_url == "https://www.linkedin.com/in/attio-profile"
    assert sync_request.person.job_title == "Founder"
    assert sync_request.company is not None
    assert sync_request.company.name == "Attio Company"
    assert sync_request.company.stage == "Series A"


def test_service_ignores_payload_fields_for_non_joined_attio_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_data = _build_approved_payload()
    payload_data["member"]["phone"] = "19998887777"
    payload_data["member"]["linkedinUrl"] = "https://www.linkedin.com/in/member-profile"
    payload_data["questions"] = [
        {
            "answer": "8511152215",
            "question": "What is your whatsapp number?",
            "semantic_key": "whatsapp_number",
        },
        {
            "answer": "https://www.linkedin.com/in/question-profile",
            "question": "What is your linked-in url?",
            "semantic_key": "linked_in_url",
        },
        {
            "answer": "Question Company",
            "question": "What is your company name?",
            "semantic_key": "company_name",
        },
        {
            "answer": "Seed",
            "question": "What is the funding stage?",
            "semantic_key": "funding_stage",
        },
    ]
    payload = MemberApprovedWebhookPayload.model_validate(payload_data)

    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            phone="+18511152215",
            linkedin_url="https://www.linkedin.com/in/attio-profile",
            job_title="CEO",
            company_name="Attio Company",
            company_stage="Seed",
        )
    )
    sync_request = keyai_webhooks.build_keyai_attio_sync_request(payload=payload)

    assert sync_request.person.phone == "+18511152215"
    assert sync_request.person.linkedin_url == "https://www.linkedin.com/in/attio-profile"
    assert sync_request.person.job_title == "CEO"
    assert sync_request.company is not None
    assert sync_request.company.name == "Attio Company"
    assert sync_request.company.stage == "Seed"
    assert sync_request.company.company_website is None


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

    def fake_invoke_gemini(prompt, config=None):
        return (
            '{"individual_blurb":"Rohan is an approved member of the Funda community.",'
            '"company_blurb":"Acme AI is the company associated with this member."}'
        )

    monkeypatch.setattr(
        keyai_webhooks,
        "invoke_gemini",
        fake_invoke_gemini,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            phone="+18511152215",
            company_name="Acme AI",
        ),
    )
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
    assert send_request.template_metadata == {
        "full_name": "Rohan Jain",
        "member_sentence": "Rohan is an approved member of the Funda community.",
        "company_sentence": "Acme AI is the company associated with this member.",
    }


def test_admin_notification_sentences_are_printed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = MemberApprovedWebhookPayload.model_validate(_build_approved_payload())

    def fake_invoke_gemini(prompt: str, config=None) -> str:
        return (
            '{"individual_blurb":"Member sentence\\n generated\\t for testing.",'
            '"company_blurb":"Company sentence\\r\\n generated for testing."}'
        )

    monkeypatch.setattr(
        keyai_webhooks,
        "invoke_gemini",
        fake_invoke_gemini,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            company_name="Acme AI",
        ),
    )

    member_sentence = keyai_webhooks.build_new_member_admin_member_sentence(payload)
    company_sentence = keyai_webhooks.build_new_member_admin_company_sentence(payload)

    print("Member sentence:", member_sentence)
    print("Company sentence:", company_sentence)

    captured = capsys.readouterr()
    assert "Member sentence: Member sentence generated for testing." in captured.out
    assert "Company sentence: Company sentence generated for testing." in captured.out


def test_service_builds_company_sentence_with_fallback_when_company_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: None,
    )

    sentence = keyai_webhooks.build_new_member_admin_company_sentence(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
    )

    assert sentence == "Company not found"


def test_service_builds_company_sentence_with_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            company_name="Acme AI",
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "invoke_gemini",
        lambda prompt, config=None: (
            '{"individual_blurb":"Founder works at Acme AI.",'
            '"company_blurb":"Acme AI builds software for finance teams.",'
            '"citations":["https://acme.ai/"]}'
        ),
    )

    sentence = keyai_webhooks.build_new_member_admin_company_sentence(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
    )

    assert sentence == "Acme AI builds software for finance teams."


def test_service_builds_admin_notification_blurbs_with_json_gemini_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            company_name="Wells Fargo",
            linkedin_url="https://www.linkedin.com/in/eshaan-vipani",
            company_stage="Public",
            job_title="Software Engineer",
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "invoke_gemini",
        lambda prompt, config=None: (
            '{"individual_blurb":"Eshaan\\nworks at Wells Fargo.",'
            '"company_blurb":"Wells Fargo\\t is a fairly solid public company.",'
            '"citations":["https://www.wellsfargo.com/"]}'
        ),
    )

    blurbs = keyai_webhooks.build_new_member_admin_blurbs(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
    )

    print("\ncitations:")
    print(blurbs.citations)

    assert blurbs.individual_blurb == "Eshaan works at Wells Fargo."
    assert blurbs.company_blurb == "Wells Fargo is a fairly solid public company."
    assert blurbs.citations == ["https://www.wellsfargo.com/"]


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


def test_service_dispatches_non_joined_event_to_lifecycle_only_attio_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_lifecycle_sync(sync_request):
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

    monkeypatch.setattr(
        keyai_webhooks,
        "get_member_context_for_member",
        lambda member_id, settings=None: AttioMemberContext(
            phone="+18511152215",
            linkedin_url="https://www.linkedin.com/in/attio-profile",
            job_title="CEO",
            company_name="Attio Company",
            company_stage="Seed",
        ),
    )
    monkeypatch.setattr(keyai_webhooks, "sync_attio_lifecycle_only", fake_lifecycle_sync)
    monkeypatch.setattr(
        keyai_webhooks,
        "sync_attio_member",
        lambda sync_request: pytest.fail("non-joined events must not upsert person/company"),
    )

    keyai_webhooks.dispatch_keyai_attio_sync(
        payload=MemberApprovedWebhookPayload.model_validate(_build_approved_payload()),
    )

    sync_request = captured["sync_request"]

    assert sync_request.event == MemberWebhookEvent.MEMBER_APPROVED
    assert sync_request.person.phone == "+18511152215"
    assert sync_request.person.linkedin_url == "https://www.linkedin.com/in/attio-profile"
    assert sync_request.person.job_title == "CEO"
    assert sync_request.company is not None
    assert sync_request.company.name == "Attio Company"


def test_service_skips_already_claimed_member_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=False,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp"),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == []


def test_service_processes_member_event_when_claimed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_attio_done",
        lambda event_id: order.append("mark_attio"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_whatsapp_done",
        lambda event_id: order.append("mark_whatsapp"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_completed",
        lambda event_id: order.append("mark_completed"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_new_member_admin_notification",
        lambda p: order.append("admin") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_admin_notification_done",
        lambda event_id: order.append("mark_admin"),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == [
        "crm",
        "mark_attio",
        "whatsapp",
        "mark_whatsapp",
        "mark_completed",
    ]


def test_service_processes_approved_member_event_with_admin_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberApprovedWebhookPayload.model_validate(_build_approved_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_new_member_admin_notification",
        lambda p: order.append("admin") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_attio_done",
        lambda event_id: order.append("mark_attio"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_whatsapp_done",
        lambda event_id: order.append("mark_whatsapp"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_admin_notification_done",
        lambda event_id: order.append("mark_admin"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_completed",
        lambda event_id: order.append("mark_completed"),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == [
        "crm",
        "mark_attio",
        "whatsapp",
        "mark_whatsapp",
        "admin",
        "mark_admin",
        "mark_completed",
    ]


def test_service_resumes_member_event_after_attio_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
            attio_done=True,
            whatsapp_done=False,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_attio_done",
        lambda event_id: order.append("mark_attio"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_whatsapp_done",
        lambda event_id: order.append("mark_whatsapp"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_completed",
        lambda event_id: order.append("mark_completed"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_new_member_admin_notification",
        lambda p: order.append("admin") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_admin_notification_done",
        lambda event_id: order.append("mark_admin"),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == [
        "whatsapp",
        "mark_whatsapp",
        "mark_completed",
    ]


def test_service_resumes_approved_member_event_before_admin_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberApprovedWebhookPayload.model_validate(_build_approved_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
            attio_done=True,
            whatsapp_done=True,
            admin_notification_done=False,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_new_member_admin_notification",
        lambda p: order.append("admin") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_admin_notification_done",
        lambda event_id: order.append("mark_admin"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_completed",
        lambda event_id: order.append("mark_completed"),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == [
        "admin",
        "mark_admin",
        "mark_completed",
    ]


def test_service_marks_member_event_failed_on_attio_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: False,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_failed",
        lambda event_id, error_message: order.append(error_message),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == ["attio_sync_failed"]


def test_service_marks_approved_member_event_failed_on_admin_notification_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberApprovedWebhookPayload.model_validate(_build_approved_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True,
            attio_done=True,
            whatsapp_done=True,
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_new_member_admin_notification",
        lambda p: False,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_failed",
        lambda event_id, error_message: order.append(error_message),
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == ["admin_notification_failed"]


def test_joined_webhook_model_allows_missing_questions() -> None:
    payload = _build_joined_payload()
    payload.pop("questions")

    webhook_payload = MemberJoinedWebhookPayload.model_validate(payload)

    assert webhook_payload.questions is None


def test_approved_webhook_model_rejects_invalid_status_transition() -> None:
    payload = _build_approved_payload()
    payload["status"] = {"old": "APPROVED", "new": "APPROVED"}

    with pytest.raises(ValidationError):
        MemberApprovedWebhookPayload.model_validate(payload)
