from datetime import datetime, UTC

import pytest

from funda_app.utils import normalize_phone_number
from funda_app.schemas.crm import (
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioPersonSyncPayload,
)
from funda_app.schemas.webhooks import MemberStatus, MemberWebhookEvent
from funda_app.services import attio
from funda_app.app_settings import AppSettings


def test_normalize_phone_number_formats_us_numbers() -> None:
    assert normalize_phone_number("9256400611") == "+19256400611"
    assert normalize_phone_number("+1 (925) 640-0611") == "+19256400611"
    assert normalize_phone_number("19256400611") == "+19256400611"


def test_sync_attio_member_posts_expected_payloads_without_company(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_calls.append(
            {
                "method": method,
                "url": url,
                "payload": payload,
                "access_token": access_token,
                "timeout_seconds": timeout_seconds,
            }
        )

        if len(captured_calls) == 1:
            return {"data": {"id": {"record_id": "person-record-123"}}}

        return {"data": {"id": {"entry_id": "entry-123"}}}

    monkeypatch.setattr(attio, "request_json", fake_request_json)

    result = attio.sync_attio_member(
        sync_request=AttioLifecycleSyncRequest(
            event=MemberWebhookEvent.MEMBER_JOINED,
            event_id="event-123",
            occurred_at=datetime(2026, 3, 14, 16, 26, 12, tzinfo=UTC),
            community_id="community-123",
            community_name="funda",
            member_status=MemberStatus.PENDING,
            person=AttioPersonSyncPayload(
                keyai_member_id="member-123",
                email="eshaan@example.com",
                full_name="Eshaan Vipani",
                first_name="Eshaan",
                last_name="Vipani",
                phone="+19256400611",
                linkedin_url="https://www.linkedin.com/in/eshaan",
            ),
        ),
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
            attio_api_key_dev="attio-token",
            attio_founder_lifecycle_list_id_dev="list-123",
        ),
    )

    assert result.status == "synced"
    assert result.person_record_id == "person-record-123"
    assert result.company_record_id is None
    assert result.lifecycle_entry_id == "entry-123"
    assert captured_calls == [
        {
            "method": "PUT",
            "url": "https://api.attio.com/v2/objects/people/records?matching_attribute=email_addresses",
            "payload": {
                "data": {
                    "values": {
                        "email_addresses": ["eshaan@example.com"],
                        "name": [
                            {
                                "first_name": "Eshaan",
                                "last_name": "Vipani",
                                "full_name": "Eshaan Vipani",
                            }
                        ],
                        "keyai_member_id": "member-123",
                        "phone_numbers": [
                            {
                                "original_phone_number": "+19256400611",
                                "country_code": "US",
                            }
                        ],
                        "linkedin": "https://www.linkedin.com/in/eshaan",
                    }
                }
            },
            "access_token": "attio-token",
            "timeout_seconds": 10.0,
        },
        {
            "method": "PUT",
            "url": "https://api.attio.com/v2/lists/list-123/entries",
            "payload": {
                "data": {
                    "parent_record_id": "person-record-123",
                    "parent_object": "people",
                    "entry_values": {
                        "member_status": "PENDING",
                        "last_keyai_event": "member.joined",
                        "last_keyai_event_id": "event-123",
                        "last_keyai_event_at": "2026-03-14T16:26:12+00:00",
                        "community_name": "funda",
                        "keyai_community_id": "community-123",
                        "joined_at": "2026-03-14T16:26:12+00:00",
                    },
                }
            },
            "access_token": "attio-token",
            "timeout_seconds": 10.0,
        },
    ]


def test_sync_attio_member_syncs_company_before_person_and_list_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_calls.append(
            {
                "method": method,
                "url": url,
                "payload": payload,
            }
        )

        if len(captured_calls) == 1:
            return {"data": []}

        if len(captured_calls) == 2:
            return {"data": {"id": {"record_id": "company-record-123"}}}

        if len(captured_calls) == 3:
            return {"data": {"id": {"record_id": "person-record-123"}}}

        return {"data": {"id": {"entry_id": "entry-123"}}}

    monkeypatch.setattr(attio, "request_json", fake_request_json)

    result = attio.sync_attio_member(
        sync_request=AttioLifecycleSyncRequest(
            event=MemberWebhookEvent.MEMBER_APPROVED,
            event_id="event-123",
            occurred_at=datetime(2026, 3, 14, 16, 26, 12, tzinfo=UTC),
            community_id="community-123",
            community_name="funda",
            member_status=MemberStatus.APPROVED,
            person=AttioPersonSyncPayload(
                keyai_member_id="member-123",
                email="eshaan@example.com",
                full_name="Eshaan Vipani",
                first_name="Eshaan",
                last_name="Vipani",
                phone="+19256400611",
                linkedin_url=None,
            ),
            company=AttioCompanySyncPayload(
                name="Acme AI",
                stage="Seed",
            ),
        ),
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
            attio_api_key_dev="attio-token",
            attio_founder_lifecycle_list_id_dev="list-123",
        ),
    )

    assert result.company_record_id == "company-record-123"
    assert captured_calls == [
        {
            "method": "POST",
            "url": "https://api.attio.com/v2/objects/companies/records/query",
            "payload": {
                "filter": {
                    "name": {
                        "value": {
                            "$eq": "Acme AI",
                        }
                    }
                },
                "limit": 1,
                "offset": 0,
            },
        },
        {
            "method": "POST",
            "url": "https://api.attio.com/v2/objects/companies/records",
            "payload": {
                "data": {
                    "values": {
                        "name": "Acme AI",
                        "company_stage": "Seed",
                    }
                }
            },
        },
        {
            "method": "PUT",
            "url": "https://api.attio.com/v2/objects/people/records?matching_attribute=email_addresses",
            "payload": {
                "data": {
                    "values": {
                        "email_addresses": ["eshaan@example.com"],
                        "name": [
                            {
                                "first_name": "Eshaan",
                                "last_name": "Vipani",
                                "full_name": "Eshaan Vipani",
                            }
                        ],
                        "keyai_member_id": "member-123",
                        "phone_numbers": [
                            {
                                "original_phone_number": "+19256400611",
                                "country_code": "US",
                            }
                        ],
                        "company": [
                            {
                                "target_object": "companies",
                                "target_record_id": "company-record-123",
                            }
                        ],
                    }
                }
            },
        },
        {
            "method": "PUT",
            "url": "https://api.attio.com/v2/lists/list-123/entries",
            "payload": {
                "data": {
                    "parent_record_id": "person-record-123",
                    "parent_object": "people",
                    "entry_values": {
                        "member_status": "APPROVED",
                        "last_keyai_event": "member.approved",
                        "last_keyai_event_id": "event-123",
                        "last_keyai_event_at": "2026-03-14T16:26:12+00:00",
                        "community_name": "funda",
                        "keyai_community_id": "community-123",
                        "approved_at": "2026-03-14T16:26:12+00:00",
                    },
                }
            },
        },
    ]


def test_sync_attio_member_asserts_company_by_domain_when_company_website_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_calls.append({"method": method, "url": url, "payload": payload})
        if "objects/companies/records?" in url:
            return {"data": {"id": {"record_id": "company-record-999"}}}
        if "objects/people/records" in url:
            return {"data": {"id": {"record_id": "person-record-999"}}}
        return {"data": {"id": {"entry_id": "entry-999"}}}

    monkeypatch.setattr(attio, "request_json", fake_request_json)

    result = attio.sync_attio_member(
        sync_request=AttioLifecycleSyncRequest(
            event=MemberWebhookEvent.MEMBER_JOINED,
            event_id="event-999",
            occurred_at=datetime(2026, 3, 14, 16, 26, 12, tzinfo=UTC),
            community_id="community-123",
            community_name="funda",
            member_status=MemberStatus.PENDING,
            person=AttioPersonSyncPayload(
                keyai_member_id="member-999",
                email="founder@example.com",
                full_name="Founder Name",
                first_name="Founder",
                last_name="Name",
            ),
            company=AttioCompanySyncPayload(
                name="Wells Fargo",
                stage="Public Company",
                company_website="https://www.wellsfargo.com/",
            ),
        ),
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
            attio_api_key_dev="attio-token",
            attio_founder_lifecycle_list_id_dev="list-123",
        ),
    )

    assert result.company_record_id == "company-record-999"
    company_call = captured_calls[0]
    assert company_call["method"] == "PUT"
    assert (
        company_call["url"]
        == "https://api.attio.com/v2/objects/companies/records?matching_attribute=domains"
    )
    assert company_call["payload"]["data"]["values"]["domains"] == [
        {"domain": "wellsfargo.com"}
    ]


def test_sync_attio_member_includes_job_title_and_company_website_in_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object],
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_calls.append({"method": method, "url": url, "payload": payload})
        if "people/records" in url:
            return {"data": {"id": {"record_id": "person-record-456"}}}
        if "companies/records" in url and "query" not in url:
            return {"data": {"id": {"record_id": "company-record-456"}}}
        if "lists" in url:
            return {"data": {"id": {"entry_id": "entry-456"}}}
        return {"data": []}

    monkeypatch.setattr(attio, "request_json", fake_request_json)

    attio.sync_attio_member(
        sync_request=AttioLifecycleSyncRequest(
            event=MemberWebhookEvent.MEMBER_JOINED,
            event_id="event-456",
            occurred_at=datetime(2026, 3, 14, 16, 26, 12, tzinfo=UTC),
            community_id="community-123",
            community_name="funda",
            member_status=MemberStatus.PENDING,
            person=AttioPersonSyncPayload(
                keyai_member_id="member-456",
                email="founder@example.com",
                full_name="Founder Name",
                first_name="Founder",
                last_name="Name",
                phone="+15551234567",
                linkedin_url="https://www.linkedin.com/in/founder",
                job_title="CEO",
            ),
            company=AttioCompanySyncPayload(
                name="Startup Inc",
                stage="Series A",
                company_website="startup.com",
            ),
        ),
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
            attio_api_key_dev="attio-token",
            attio_founder_lifecycle_list_id_dev="list-123",
        ),
    )

    person_call = next(c for c in captured_calls if "people/records" in c["url"])
    assert person_call["payload"]["data"]["values"]["job_title"] == "CEO"

    company_call = next(
        c
        for c in captured_calls
        if "companies/records" in c["url"] and "query" not in c["url"]
    )
    assert company_call["payload"]["data"]["values"]["company_website"] == "startup.com"
