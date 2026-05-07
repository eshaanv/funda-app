from datetime import UTC, datetime

from funda_app.schemas.crm import AttioCompanySyncPayload, AttioPersonSyncPayload
from funda_app.schemas.customers import KeyAICustomerSyncRequest
from funda_app.schemas.webhooks import MemberStatus, MemberWebhookEvent
from funda_app.services import customers


def _build_customer_sync_request(
    event: MemberWebhookEvent = MemberWebhookEvent.MEMBER_JOINED,
    previous_status: MemberStatus | None = None,
    member_status: MemberStatus = MemberStatus.PENDING,
    company: AttioCompanySyncPayload | None = AttioCompanySyncPayload(
        name="Acme AI",
        stage="Seed",
        company_website="https://acme.ai",
    ),
    question_answers: dict[str, str] | None = None,
    keyai_questions: list[dict[str, object]] | None = None,
) -> KeyAICustomerSyncRequest:
    return KeyAICustomerSyncRequest(
        event=event,
        event_id="event-123",
        occurred_at=datetime(2026, 3, 13, 15, 5, 32, tzinfo=UTC),
        community_id="community-123",
        community_name="funda",
        previous_status=previous_status,
        member_status=member_status,
        person=AttioPersonSyncPayload(
            keyai_member_id="member-123",
            email="rohan@example.com",
            full_name="Rohan Jain",
            first_name="Rohan",
            last_name="Jain",
            phone="+18511152215",
            linkedin_url="https://www.linkedin.com/in/rohan-jain",
            job_title="Founder",
        ),
        company=company,
        question_answers=question_answers or {},
        keyai_questions=keyai_questions or [],
    )


def test_customer_document_update_includes_joined_profile_and_lifecycle_fields() -> (
    None
):
    synced_at = datetime(2026, 3, 13, 16, 0, tzinfo=UTC)
    update = customers._build_customer_document_update(
        sync_request=_build_customer_sync_request(),
        document_exists=False,
        synced_at=synced_at,
    )

    assert update == {
        "member_id": "member-123",
        "community_id": "community-123",
        "community_name": "funda",
        "member_status": "PENDING",
        "latest_event": "member.joined",
        "latest_event_id": "event-123",
        "latest_event_at": datetime(2026, 3, 13, 15, 5, 32, tzinfo=UTC),
        "updated_at": synced_at,
        "joined_at": datetime(2026, 3, 13, 15, 5, 32, tzinfo=UTC),
        "created_at": synced_at,
        "first_event": "member.joined",
        "first_event_id": "event-123",
        "first_event_at": datetime(2026, 3, 13, 15, 5, 32, tzinfo=UTC),
        "email": "rohan@example.com",
        "full_name": "Rohan Jain",
        "first_name": "Rohan",
        "last_name": "Jain",
        "phone": "+18511152215",
        "linkedin_url": "https://www.linkedin.com/in/rohan-jain",
        "job_title": "Founder",
        "company_name": "Acme AI",
        "company_stage": "Seed",
        "company_website": "https://acme.ai",
    }


def test_customer_document_update_preserves_missing_company_fields() -> None:
    synced_at = datetime(2026, 3, 13, 16, 0, tzinfo=UTC)
    sync_request = _build_customer_sync_request(
        event=MemberWebhookEvent.MEMBER_APPROVED,
        previous_status=MemberStatus.PENDING,
        member_status=MemberStatus.APPROVED,
        company=None,
    )
    sync_request.person.phone = None
    sync_request.person.linkedin_url = None
    sync_request.person.job_title = None

    update = customers._build_customer_document_update(
        sync_request=sync_request,
        document_exists=True,
        synced_at=synced_at,
    )

    assert "created_at" not in update
    assert "company_name" not in update
    assert "phone" not in update
    assert update["member_status"] == "APPROVED"
    assert update["latest_event"] == "member.approved"
    assert update["approved_at"] == datetime(2026, 3, 13, 15, 5, 32, tzinfo=UTC)


def test_customer_event_document_includes_status_transition_and_snapshot() -> None:
    synced_at = datetime(2026, 3, 13, 16, 0, tzinfo=UTC)
    event = customers._build_customer_event_document(
        sync_request=_build_customer_sync_request(
            event=MemberWebhookEvent.MEMBER_APPROVED,
            previous_status=MemberStatus.PENDING,
            member_status=MemberStatus.APPROVED,
        ),
        synced_at=synced_at,
    )

    assert event["event_id"] == "event-123"
    assert event["event_type"] == "member.approved"
    assert event["old_status"] == "PENDING"
    assert event["new_status"] == "APPROVED"
    assert event["person"] == {
        "member_id": "member-123",
        "email": "rohan@example.com",
        "full_name": "Rohan Jain",
        "first_name": "Rohan",
        "last_name": "Jain",
        "phone": "+18511152215",
        "linkedin_url": "https://www.linkedin.com/in/rohan-jain",
        "job_title": "Founder",
    }
    assert event["company"] == {
        "name": "Acme AI",
        "stage": "Seed",
        "company_website": "https://acme.ai",
    }


def test_customer_document_and_event_include_canonical_question_answers() -> None:
    synced_at = datetime(2026, 3, 13, 16, 0, tzinfo=UTC)
    sync_request = _build_customer_sync_request(
        question_answers={
            "fund_website": "https://fund.example",
            "services_value_offered": "Office hours",
        },
        keyai_questions=[
            {
                "canonical_key": "fund_website",
                "semantic_key": "fund_site",
                "question": "Fund Website?",
                "type": "short_text",
                "answer": "https://fund.example",
                "normalized_answer": "https://fund.example",
            }
        ],
    )

    update = customers._build_customer_document_update(
        sync_request=sync_request,
        document_exists=True,
        synced_at=synced_at,
    )
    event = customers._build_customer_event_document(
        sync_request=sync_request,
        synced_at=synced_at,
    )

    assert update["fund_website"] == "https://fund.example"
    assert update["services_value_offered"] == "Office hours"
    assert update["question_answers"] == {
        "fund_website": "https://fund.example",
        "services_value_offered": "Office hours",
    }
    assert update["keyai_questions"] == [
        {
            "canonical_key": "fund_website",
            "semantic_key": "fund_site",
            "question": "Fund Website?",
            "type": "short_text",
            "answer": "https://fund.example",
            "normalized_answer": "https://fund.example",
        }
    ]
    assert event["question_answers"] == update["question_answers"]
    assert event["keyai_questions"] == update["keyai_questions"]
