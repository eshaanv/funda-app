import pytest

from funda_app.schemas.enrichment import EnrichmentRequest
from funda_app.schemas.webhooks import MemberJoinedWebhookPayload
from funda_app.services import keyai_webhooks, member_enrichment


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

    request = member_enrichment.build_enrichment_request(payload)

    assert request == EnrichmentRequest(
        member_id="14b8d602-1eee-11f1-b904-0242ac14000a",
        event_id="08964b2f-d41e-4ae4-aa9f-bfb87b48c94f",
        community_name="funda",
        occurred_at=payload.occurredAt,
        first_name="Rohan",
        last_name="Jain",
        full_name="Rohan Jain",
        email="rohan+1@key.ai",
        phone="8511152215",
        linkedin_url="https://www.linkedin.com/in/rohan-jain",
        company_name="Acme AI",
        company_stage="Seed",
    )


def test_build_enrichment_request_prefers_top_level_fields() -> None:
    payload_data = _build_joined_payload()
    payload_data["member"]["linkedinUrl"] = "https://www.linkedin.com/in/top-level"
    payload_data["member"]["companyName"] = "Top Level Inc"
    payload_data["member"]["companyStage"] = "Series A"
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    request = member_enrichment.build_enrichment_request(payload)

    assert request is not None
    assert request.linkedin_url == "https://www.linkedin.com/in/top-level"
    assert request.company_name == "Top Level Inc"
    assert request.company_stage == "Series A"


def test_build_enrichment_request_returns_none_without_linkedin() -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"] = []
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    request = member_enrichment.build_enrichment_request(payload)

    assert request is None


def test_dispatch_member_joined_enrichment_skips_without_linkedin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_data = _build_joined_payload()
    payload_data["questions"] = []
    payload = MemberJoinedWebhookPayload.model_validate(payload_data)

    monkeypatch.setattr(
        member_enrichment,
        "invoke_gemini",
        lambda prompt, config: pytest.fail("invoke_gemini should not be called"),
    )

    member_enrichment.dispatch_member_joined_enrichment(payload)


def test_enrich_member_returns_completed_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = EnrichmentRequest(
        member_id="member-123",
        event_id="event-123",
        community_name="funda",
        occurred_at=MemberJoinedWebhookPayload.model_validate(
            _build_joined_payload()
        ).occurredAt,
        first_name="Rohan",
        last_name="Jain",
        full_name="Rohan Jain",
        email="rohan+1@key.ai",
        phone="8511152215",
        linkedin_url="https://www.linkedin.com/in/rohan-jain",
        company_name="Acme AI",
        company_stage="Seed",
    )
    monkeypatch.setattr(
        member_enrichment,
        "invoke_gemini",
        lambda prompt, config: "Rohan joined from Acme AI at Seed stage.",
    )

    result = member_enrichment.enrich_member(request)

    assert result.status == "completed"
    assert result.summary == "Rohan joined from Acme AI at Seed stage."


def test_enrich_member_returns_failed_record_when_gemini_has_no_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = EnrichmentRequest(
        member_id="member-123",
        event_id="event-123",
        community_name="funda",
        occurred_at=MemberJoinedWebhookPayload.model_validate(
            _build_joined_payload()
        ).occurredAt,
        first_name="Rohan",
        last_name="Jain",
        full_name="Rohan Jain",
        email="rohan+1@key.ai",
        phone="8511152215",
        linkedin_url="https://www.linkedin.com/in/rohan-jain",
        company_name="Acme AI",
        company_stage="Seed",
    )
    monkeypatch.setattr(member_enrichment, "invoke_gemini", lambda prompt, config: None)

    result = member_enrichment.enrich_member(request)

    assert result.status == "failed"
    assert result.reason == "gemini_no_response"


def test_dispatch_keyai_joined_member_tasks_runs_crm_before_enrichment_and_whatsapp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    payload = MemberJoinedWebhookPayload.model_validate(_build_joined_payload())

    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_attio_sync",
        lambda joined_payload: order.append("crm"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_member_joined_enrichment",
        lambda joined_payload: order.append("enrichment"),
    )
    monkeypatch.setattr(
        keyai_webhooks,
        "dispatch_keyai_whatsapp_message",
        lambda joined_payload: order.append("whatsapp"),
    )

    keyai_webhooks.dispatch_keyai_joined_member_tasks(payload)

    assert order == ["crm", "enrichment", "whatsapp"]
