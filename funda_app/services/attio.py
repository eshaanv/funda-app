from collections.abc import Mapping
from urllib import parse

from funda_app.schemas.crm import (
    ATTIO_SCHEMA,
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioSyncResult,
)
from funda_app.app_settings import AppSettings, get_app_settings
from funda_app.utils.http import request_json


def sync_attio_member(
    sync_request: AttioLifecycleSyncRequest,
    settings: AppSettings | None = None,
) -> AttioSyncResult:
    """
    Syncs a Key.ai member lifecycle event into Attio.

    Args:
        sync_request (AttioLifecycleSyncRequest): Normalized lifecycle sync request.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        AttioSyncResult: IDs for the synchronized Attio records.

    Raises:
        ValueError: If Attio is not configured or required member fields are missing.
        urllib.error.HTTPError: If the Attio API rejects the request.
        urllib.error.URLError: If the Attio API is unreachable.
    """
    runtime_settings = settings or get_app_settings()
    _validate_attio_settings(runtime_settings)

    company_record_id = None
    if sync_request.company is not None:
        company_record_id = _sync_company(
            company=sync_request.company,
            settings=runtime_settings,
        )

    person_record_id = _assert_person_record(
        sync_request=sync_request,
        company_record_id=company_record_id,
        settings=runtime_settings,
    )
    lifecycle_entry_id = _assert_lifecycle_entry(
        sync_request=sync_request,
        person_record_id=person_record_id,
        settings=runtime_settings,
    )

    return AttioSyncResult(
        status="synced",
        person_record_id=person_record_id,
        company_record_id=company_record_id,
        lifecycle_entry_id=lifecycle_entry_id,
    )


def _validate_attio_settings(settings: AppSettings) -> None:
    if settings.attio_api_key is None or not settings.attio_api_key.strip():
        raise ValueError(f"Set the Attio API key in env - {settings.app_env}")

    if (
        settings.attio_founder_lifecycle_list_id is None
        or not settings.attio_founder_lifecycle_list_id.strip()
    ):
        raise ValueError(
            f"Set the Attio founder lifecycle id in env - {settings.app_env}"
        )


def _sync_company(company: AttioCompanySyncPayload, settings: AppSettings) -> str:
    existing_record_id = _find_company_record_id_by_name(
        company_name=company.name,
        settings=settings,
    )

    if existing_record_id is None:
        response = request_json(
            method="POST",
            url=(
                f"{settings.attio_base_url.rstrip('/')}/objects/"
                f"{ATTIO_SCHEMA.company.object_slug}/records"
            ),
            payload={
                "data": {
                    "values": _build_company_values(
                        company=company,
                    )
                }
            },
            access_token=settings.attio_api_key or "",
            timeout_seconds=settings.attio_timeout_seconds,
        )
        return _extract_record_id(response)

    request_json(
        method="PATCH",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.company.object_slug}/records/"
            f"{existing_record_id}"
        ),
        payload={
            "data": {
                "values": _build_company_values(
                    company=company,
                )
            }
        },
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return existing_record_id


def _find_company_record_id_by_name(
    company_name: str, settings: AppSettings
) -> str | None:
    response = request_json(
        method="POST",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.company.object_slug}/records/query"
        ),
        payload={
            "filter": {
                ATTIO_SCHEMA.company.name_attribute: {
                    "value": {
                        "$eq": company_name,
                    }
                }
            },
            "limit": 1,
            "offset": 0,
        },
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    records = response.get("data", [])
    if not records:
        return None

    return records[0]["id"]["record_id"]


def _assert_person_record(
    sync_request: AttioLifecycleSyncRequest,
    company_record_id: str | None,
    settings: AppSettings,
) -> str:
    if not sync_request.person.email.strip():
        raise ValueError("Attio person sync requires an email address")

    query = parse.urlencode(
        {"matching_attribute": ATTIO_SCHEMA.person.matching_attribute}
    )
    response = request_json(
        method="PUT",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.person.object_slug}/records?{query}"
        ),
        payload={
            "data": {
                "values": _build_person_values(
                    sync_request=sync_request,
                    company_record_id=company_record_id,
                )
            }
        },
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return _extract_record_id(response)


def _assert_lifecycle_entry(
    sync_request: AttioLifecycleSyncRequest,
    person_record_id: str,
    settings: AppSettings,
) -> str:
    response = request_json(
        method="PUT",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/lists/"
            f"{settings.attio_founder_lifecycle_list_id}/entries"
        ),
        payload={
            "data": {
                "parent_record_id": person_record_id,
                "parent_object": ATTIO_SCHEMA.lifecycle.parent_object,
                "entry_values": _build_lifecycle_entry_values(
                    sync_request=sync_request,
                ),
            }
        },
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return _extract_entry_id(response)


def _build_person_values(
    sync_request: AttioLifecycleSyncRequest,
    company_record_id: str | None,
) -> dict[str, object]:
    values: dict[str, object] = {
        ATTIO_SCHEMA.person.email_attribute: [sync_request.person.email],
        ATTIO_SCHEMA.person.name_attribute: [
            {
                "first_name": sync_request.person.first_name,
                "last_name": sync_request.person.last_name,
                "full_name": sync_request.person.full_name,
            }
        ],
        ATTIO_SCHEMA.person.external_id_attribute: sync_request.person.keyai_member_id,
    }

    normalized_phone = sync_request.person.phone
    if normalized_phone is not None:
        phone_value: dict[str, str] = {"original_phone_number": normalized_phone}
        country_code = _get_country_code(normalized_phone)
        if country_code is not None:
            phone_value["country_code"] = country_code

        values[ATTIO_SCHEMA.person.phone_attribute] = [phone_value]

    if sync_request.person.linkedin_url is not None:
        values[ATTIO_SCHEMA.person.linkedin_attribute] = (
            sync_request.person.linkedin_url
        )

    if sync_request.person.job_title is not None:
        values[ATTIO_SCHEMA.person.job_title_attribute] = sync_request.person.job_title

    if company_record_id is not None:
        values[ATTIO_SCHEMA.person.company_relationship_attribute] = [
            {
                "target_object": ATTIO_SCHEMA.company.object_slug,
                "target_record_id": company_record_id,
            }
        ]

    return values


def _build_company_values(
    company: AttioCompanySyncPayload,
) -> dict[str, object]:
    values: dict[str, object] = {ATTIO_SCHEMA.company.name_attribute: company.name}
    if company.stage is not None:
        values[ATTIO_SCHEMA.company.stage_attribute] = company.stage
    if company.company_website is not None:
        values[ATTIO_SCHEMA.company.company_website_attribute] = company.company_website

    return values


def _build_lifecycle_entry_values(
    sync_request: AttioLifecycleSyncRequest,
) -> dict[str, object]:
    entry_values: dict[str, object] = {
        ATTIO_SCHEMA.lifecycle.status_attribute: sync_request.member_status.value,
        ATTIO_SCHEMA.lifecycle.last_event_attribute: sync_request.event.value,
        ATTIO_SCHEMA.lifecycle.last_event_id_attribute: sync_request.event_id,
        ATTIO_SCHEMA.lifecycle.last_event_at_attribute: sync_request.occurred_at.isoformat(),
        ATTIO_SCHEMA.lifecycle.community_name_attribute: sync_request.community_name,
        ATTIO_SCHEMA.lifecycle.community_id_attribute: sync_request.community_id,
    }
    timestamp_attribute = ATTIO_SCHEMA.lifecycle.timestamp_attribute_for_event(
        sync_request.event
    )
    entry_values[timestamp_attribute] = sync_request.occurred_at.isoformat()
    return entry_values


def _get_country_code(phone_number: str) -> str | None:
    if phone_number.startswith("+1"):
        return "US"

    return None


def _extract_record_id(response: Mapping[str, object]) -> str:
    return response["data"]["id"]["record_id"]


def _extract_entry_id(response: Mapping[str, object]) -> str:
    return response["data"]["id"]["entry_id"]
