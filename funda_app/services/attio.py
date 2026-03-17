import logging
from collections.abc import Mapping
from urllib import error, parse

from funda_app.schemas.crm import (
    ATTIO_SCHEMA,
    AttioCompanySyncPayload,
    AttioLifecycleSyncRequest,
    AttioSyncResult,
)
from funda_app.app_settings import AppSettings, get_app_settings
from funda_app.utils.domain import normalize_domain
from funda_app.utils.http import request_json

logger = logging.getLogger(__name__)


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


def get_linked_company_name_for_member(
    member_id: str,
    settings: AppSettings | None = None,
) -> str | None:
    """
    Returns the linked Attio company name for a Key.ai member ID.

    Args:
        member_id (str): Key.ai member ID stored on the person record.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        str | None: Linked company name when found, otherwise None.
    """
    runtime_settings = settings or get_app_settings()
    _validate_attio_settings(runtime_settings)

    person_record = _find_person_record_by_member_id(
        member_id=member_id,
        settings=runtime_settings,
    )
    if person_record is None:
        return None

    company_record_id = _extract_company_record_id_from_person(person_record)
    if company_record_id is None:
        return None

    company_record = request_json(
        method="GET",
        url=(
            f"{runtime_settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.company.object_slug}/records/{company_record_id}"
        ),
        payload={},
        access_token=runtime_settings.attio_api_key or "",
        timeout_seconds=runtime_settings.attio_timeout_seconds,
    )
    return _extract_company_name_from_record(company_record.get("data"))


def get_latest_lifecycle_event_id_for_member(
    member_id: str,
    settings: AppSettings | None = None,
) -> str | None:
    """
    Returns the most recent lifecycle event ID stored for a Key.ai member.

    Args:
        member_id (str): Key.ai member ID stored on the person record.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        str | None: Latest stored lifecycle event ID when found, otherwise None.
    """
    runtime_settings = settings or get_app_settings()
    _validate_attio_settings(runtime_settings)

    person_record = _find_person_record_by_member_id(
        member_id=member_id,
        settings=runtime_settings,
    )
    if person_record is None:
        return None

    person_record_id = _extract_record_id_from_data(person_record.get("id"))
    if person_record_id is None:
        return None

    response = request_json(
        method="POST",
        url=(
            f"{runtime_settings.attio_base_url.rstrip('/')}/lists/"
            f"{runtime_settings.attio_founder_lifecycle_list_id}/entries/query"
        ),
        payload={
            "filter": {
                "parent_record_id": {
                    "$eq": person_record_id,
                }
            },
            "limit": 1,
            "offset": 0,
        },
        access_token=runtime_settings.attio_api_key or "",
        timeout_seconds=runtime_settings.attio_timeout_seconds,
    )
    entries = response.get("data", [])
    if not entries:
        return None

    return _extract_lifecycle_event_id_from_entry(entries[0])


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
    domain = normalize_domain(company.company_website)
    if domain is not None:
        query = parse.urlencode(
            {"matching_attribute": ATTIO_SCHEMA.company.domains_attribute}
        )
        response = _request_json_with_company_fallback(
            method="PUT",
            url=(
                f"{settings.attio_base_url.rstrip('/')}/objects/"
                f"{ATTIO_SCHEMA.company.object_slug}/records?{query}"
            ),
            company=company,
            settings=settings,
            domain=domain,
        )
        return _extract_record_id(response)

    existing_record_id = _find_company_record_id_by_name(
        company_name=company.name,
        settings=settings,
    )

    if existing_record_id is None:
        response = _request_json_with_company_fallback(
            method="POST",
            url=(
                f"{settings.attio_base_url.rstrip('/')}/objects/"
                f"{ATTIO_SCHEMA.company.object_slug}/records"
            ),
            company=company,
            settings=settings,
        )
        return _extract_record_id(response)

    _request_json_with_company_fallback(
        method="PATCH",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.company.object_slug}/records/"
            f"{existing_record_id}"
        ),
        company=company,
        settings=settings,
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


def _find_person_record_by_member_id(
    member_id: str,
    settings: AppSettings,
) -> Mapping[str, object] | None:
    response = request_json(
        method="POST",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.person.object_slug}/records/query"
        ),
        payload={
            "filter": {
                ATTIO_SCHEMA.person.external_id_attribute: {
                    "value": {
                        "$eq": member_id,
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

    return records[0]


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
    response = _request_json_with_person_fallback(
        method="PUT",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/objects/"
            f"{ATTIO_SCHEMA.person.object_slug}/records?{query}"
        ),
        sync_request=sync_request,
        company_record_id=company_record_id,
        settings=settings,
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
    include_optional_fields: bool = True,
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

    if include_optional_fields and sync_request.person.linkedin_url is not None:
        values[ATTIO_SCHEMA.person.linkedin_attribute] = (
            sync_request.person.linkedin_url
        )

    if include_optional_fields and sync_request.person.job_title is not None:
        values[ATTIO_SCHEMA.person.job_title_attribute] = sync_request.person.job_title

    if include_optional_fields and company_record_id is not None:
        values[ATTIO_SCHEMA.person.company_relationship_attribute] = [
            {
                "target_object": ATTIO_SCHEMA.company.object_slug,
                "target_record_id": company_record_id,
            }
        ]

    return values


def _build_company_values(
    company: AttioCompanySyncPayload,
    domain: str | None = None,
    include_optional_fields: bool = True,
) -> dict[str, object]:
    values: dict[str, object] = {ATTIO_SCHEMA.company.name_attribute: company.name}
    if domain is not None:
        values[ATTIO_SCHEMA.company.domains_attribute] = [{"domain": domain}]
    if include_optional_fields and company.stage is not None:
        values[ATTIO_SCHEMA.company.stage_attribute] = company.stage
    if include_optional_fields and company.company_website is not None:
        values[ATTIO_SCHEMA.company.company_website_attribute] = company.company_website

    return values


def _request_json_with_company_fallback(
    method: str,
    url: str,
    company: AttioCompanySyncPayload,
    settings: AppSettings,
    domain: str | None = None,
) -> dict[str, object]:
    payload = {
        "data": {
            "values": _build_company_values(
                company=company,
                domain=domain,
            )
        }
    }
    try:
        return request_json(
            method=method,
            url=url,
            payload=payload,
            access_token=settings.attio_api_key or "",
            timeout_seconds=settings.attio_timeout_seconds,
        )
    except error.HTTPError as exc:
        if exc.code != 400 or (
            company.stage is None and company.company_website is None
        ):
            raise

        logger.warning(
            "Attio company sync rejected optional fields; retrying with required values only: %s",
            exc.msg,
        )
        fallback_payload = {
            "data": {
                "values": _build_company_values(
                    company=company,
                    domain=domain,
                    include_optional_fields=False,
                )
            }
        }
        return request_json(
            method=method,
            url=url,
            payload=fallback_payload,
            access_token=settings.attio_api_key or "",
            timeout_seconds=settings.attio_timeout_seconds,
        )


def _request_json_with_person_fallback(
    method: str,
    url: str,
    sync_request: AttioLifecycleSyncRequest,
    company_record_id: str | None,
    settings: AppSettings,
) -> dict[str, object]:
    payload = {
        "data": {
            "values": _build_person_values(
                sync_request=sync_request,
                company_record_id=company_record_id,
            )
        }
    }
    try:
        return request_json(
            method=method,
            url=url,
            payload=payload,
            access_token=settings.attio_api_key or "",
            timeout_seconds=settings.attio_timeout_seconds,
        )
    except error.HTTPError as exc:
        if exc.code != 400 or (
            sync_request.person.linkedin_url is None
            and sync_request.person.job_title is None
            and company_record_id is None
        ):
            raise

        logger.warning(
            "Attio person sync rejected optional fields; retrying with required values only: %s",
            exc.msg,
        )
        fallback_payload = {
            "data": {
                "values": _build_person_values(
                    sync_request=sync_request,
                    company_record_id=None,
                    include_optional_fields=False,
                )
            }
        }
        return request_json(
            method=method,
            url=url,
            payload=fallback_payload,
            access_token=settings.attio_api_key or "",
            timeout_seconds=settings.attio_timeout_seconds,
        )


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


def _extract_record_id_from_data(data: object) -> str | None:
    if not isinstance(data, Mapping):
        return None

    record_id = data.get("record_id")
    if isinstance(record_id, str) and record_id.strip():
        return record_id

    return None


def _extract_company_record_id_from_person(
    person_record: Mapping[str, object],
) -> str | None:
    values = person_record.get("values", {})
    if not isinstance(values, Mapping):
        return None

    company_values = values.get(ATTIO_SCHEMA.person.company_relationship_attribute, [])
    if not isinstance(company_values, list) or not company_values:
        return None

    first_company = company_values[0]
    if not isinstance(first_company, Mapping):
        return None

    record_id = first_company.get("target_record_id")
    if isinstance(record_id, str) and record_id.strip():
        return record_id

    nested_target = first_company.get("target_record")
    if isinstance(nested_target, Mapping):
        nested_id = nested_target.get("id")
        if isinstance(nested_id, Mapping):
            record_id = nested_id.get("record_id")
            if isinstance(record_id, str) and record_id.strip():
                return record_id

    return None


def _extract_company_name_from_record(
    company_record: object,
) -> str | None:
    if not isinstance(company_record, Mapping):
        return None

    values = company_record.get("values", {})
    if not isinstance(values, Mapping):
        return None

    company_name = values.get(ATTIO_SCHEMA.company.name_attribute)
    if isinstance(company_name, str) and company_name.strip():
        return company_name.strip()

    if isinstance(company_name, list) and company_name:
        first_value = company_name[0]
        if isinstance(first_value, Mapping):
            value = first_value.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _extract_lifecycle_event_id_from_entry(
    entry: object,
) -> str | None:
    if not isinstance(entry, Mapping):
        return None

    entry_values = entry.get("entry_values", {})
    if not isinstance(entry_values, Mapping):
        return None

    event_value = entry_values.get(ATTIO_SCHEMA.lifecycle.last_event_id_attribute)
    if isinstance(event_value, str) and event_value.strip():
        return event_value.strip()

    if isinstance(event_value, list) and event_value:
        first_value = event_value[0]
        if isinstance(first_value, Mapping):
            value = first_value.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()

    if isinstance(event_value, Mapping):
        value = event_value.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None
