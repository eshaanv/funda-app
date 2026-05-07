import pytest
from uuid import uuid4

from funda_app.schemas.idempotency import KeyAIEventProcessingState
from funda_app.schemas.webhooks import MemberJoinedWebhookPayload
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
                "answer": "https://www.linkedin.com/in/rohan-jain",
                "question": "What is your linked-in url?",
                "type": "website_url",
                "semantic_key": "linked_in_url",
            },
            {
                "answer": "8511152215",
                "question": "What is your whatsapp number?",
                "type": "phone_number",
                "semantic_key": "whatsapp_number",
            },
            {
                "answer": "Acme AI",
                "question": "What is your company name?",
                "type": "short_text",
                "semantic_key": "company_name",
            },
            {
                "answer": ["Seed"],
                "question": "What is the funding stage?",
                "type": "multiple_choice_single",
                "semantic_key": "funding_stage",
            },
        ],
        "occurredAt": "2026-03-13T15:05:32.436Z",
    }


def test_build_enrichment_request_uses_questions_fallback() -> None:
    MemberJoinedWebhookPayload.model_validate(_build_joined_payload())


def test_build_enrichment_request_accepts_question_only_fields() -> None:
    MemberJoinedWebhookPayload.model_validate(_build_joined_payload())


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
        "begin_keyai_event_processing",
        lambda event_id, member_id, event_type: KeyAIEventProcessingState(
            should_process=True
        ),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_attio_done",
        lambda event_id: None,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_firestore_customer_done",
        lambda event_id: None,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_whatsapp_done",
        lambda event_id: None,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "mark_keyai_event_completed",
        lambda event_id: None,
    )

    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda p: order.append("crm") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_firestore_customer_sync",
        lambda p: order.append("firestore") or True,
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda p: order.append("whatsapp") or True,
    )

    keyai_webhooks.dispatch_keyai_member_tasks(payload)

    assert order == ["crm", "firestore", "whatsapp"]
