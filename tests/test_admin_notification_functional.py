import os

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
                "email": "eshaanvipani1@gmail.com",
                "phone": "8511152215",
                "fullName": "Eshaan Vipani",
                "lastName": "Vipani",
                "firstName": "Eshaan",
                "companyName": "Wells Fargo",
                "linkedinUrl": "https://www.linkedin.com/in/eshaan-vipani/",
                "companyStage": "Public Company",
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
    )

    member_sentence = keyai_webhooks.build_new_member_admin_member_sentence(payload)
    company_sentence = keyai_webhooks.build_new_member_admin_company_sentence(payload)

    print("\nmember_sentence:")
    print(member_sentence)
    print("\ncompany_sentence:")
    print(company_sentence)

    assert member_sentence
    assert company_sentence
    assert member_sentence != "Eshaan Vipani is an approved member of the Funda community."
    assert company_sentence != "Wells Fargo is the company associated with this member."
    assert company_sentence != "Company not found"
