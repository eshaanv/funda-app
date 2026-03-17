import pytest

from funda_app.schemas.webhooks import MemberJoinedWebhookPayload
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


def test_build_enrichment_request_uses_questions_fallback() -> None:
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())


def test_build_enrichment_request_prefers_top_level_fields() -> None:
    payload_data = _build_joined_payload()
    payload_data["member"]["linkedinUrl"] = "https://www.linkedin.com/in/top-level"
    payload_data["member"]["companyName"] = "Top Level Inc"
    payload_data["member"]["companyStage"] = "Series A"
    MemberJoinedWebhookPayload.model_validate(payload_data)


def test_build_enrichment_request_returns_none_without_linkedin() -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"] = []
    MemberJoinedWebhookPayload.model_validate(payload_data)


def test_dispatch_member_joined_enrichment_skips_without_linkedin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"] = []
    MemberJoinedWebhookPayload.model_validate(payload_data)


def test_enrich_member_returns_completed_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MemberJoinedWebhookPayload.model_validate(_build_joined_payload())


def test_enrich_member_returns_failed_record_when_gemini_has_no_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    MemberJoinedWebhookPayload.model_validate(_build_joined_payload())


def test_dispatch_keyai_member_tasks_runs_crm_before_whatsapp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

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

    assert order == ["crm", "whatsapp"]
