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
                "id": "user-456",
                "email": "dakshata@example.com",
                "phone": "8511152215",
                "fullName": "Dakshata Anand",
                "lastName": "Anand",
                "firstName": "Dakshata",
                "companyName": "Ontra",
                "linkedinUrl": "https://www.linkedin.com/in/dakshata-anand/",
                "companyStage": "Series B",
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
            "questions": [
                {
                    "question": "What is your current job title?",
                    "answer": "Business Development Associate - Investment Banking",
                },
                {
                    "question": "What is your company website domain?",
                    "answer": "https://www.ontra.ai/",
                },
                {
                    "question": "What is your company's funding stage?",
                    "answer": "Series B",
                },
            ],
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
    assert "Ontra" in member_sentence
    assert "Ontra" in company_sentence
    assert member_sentence != "Dakshata Anand is an approved member of the Funda community."
    assert company_sentence != "Ontra is the company associated with this member."
    assert company_sentence != "Company not found"
