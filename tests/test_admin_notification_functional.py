import os
from uuid import uuid4

import pytest

from funda_app.schemas.webhooks import MemberApprovedWebhookPayload
from funda_app.services import keyai_webhooks


def _live_gemini_test_enabled() -> bool:
    return os.environ.get("RUN_LIVE_GEMINI_TESTS") == "1"


@pytest.mark.skipif(
    not _live_gemini_test_enabled(),
    reason="Set RUN_LIVE_GEMINI_TESTS=1 to run the live Gemini functional test.",
)
def test_live_new_member_admin_sentence_generation() -> None:
    payload = MemberApprovedWebhookPayload.model_validate(
        {
            "event": "member.approved",
            "member": {
                "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
                "email": "eshaanvipani1@gmail.com",
                "phone": "9256400611",
                "fullName": "Eshaan Vipani",
                "lastName": "Vipani",
                "firstName": "Eshaan",
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
    )

    member_sentence = keyai_webhooks.build_new_member_admin_member_sentence(payload)
    company_sentence = keyai_webhooks.build_new_member_admin_company_sentence(payload)

    print("\nmember_sentence:")
    print(member_sentence)
    print("\ncompany_sentence:")
    print(company_sentence)

    assert member_sentence
    assert company_sentence
    assert "\n" not in member_sentence
    assert "\n" not in company_sentence
    assert len(member_sentence) <= 180
    assert len(company_sentence) <= 140
    assert "Wells Fargo" in company_sentence
    assert member_sentence != "Eshaan Vipani is an approved member of the Funda community."
    assert company_sentence != "Wells Fargo is the company associated with this member."
    assert company_sentence != "Company not found"
