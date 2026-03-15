import pytest

from funda_app.app_settings import AppSettings
from funda_app.schemas.crm import (
    ATTIO_SCHEMA,
    AttioLiveAttribute,
    AttioListState,
    AttioWorkspaceSchemaSnapshot,
)
from funda_app.services import attio_schema


def test_plan_attio_schema_changes_creates_missing_list_and_custom_attributes() -> None:
    snapshot = AttioWorkspaceSchemaSnapshot(
        people_attributes=(
            _live_attribute("email_addresses", "Email Addresses", "email-address"),
            _live_attribute("name", "Name", "personal-name"),
            _live_attribute("phone_numbers", "Phone Numbers", "phone-number"),
            _live_attribute("company", "Company", "record-reference"),
        ),
        company_attributes=(_live_attribute("name", "Name", "text"),),
        lifecycle_list=None,
    )

    plan = attio_schema.plan_attio_schema_changes(snapshot=snapshot)

    assert not plan.issues
    assert len(plan.actions) == 15
    assert [action.kind for action in plan.actions[:4]] == [
        "create_attribute",
        "create_attribute",
        "create_attribute",
        "create_list",
    ]
    assert {
        action.api_slug for action in plan.actions if action.api_slug is not None
    } == {
        "keyai_member_id",
        "linkedin",
        "company_stage",
        "member_status",
        "last_keyai_event",
        "last_keyai_event_id",
        "last_keyai_event_at",
        "community_name",
        "keyai_community_id",
        "joined_at",
        "approved_at",
        "rejected_at",
        "removed_at",
        "left_at",
    }


def test_plan_attio_schema_changes_reports_missing_required_and_type_drift() -> None:
    snapshot = AttioWorkspaceSchemaSnapshot(
        people_attributes=(
            _live_attribute("email_addresses", "Email Addresses", "email-address"),
            _live_attribute("name", "Name", "personal-name"),
            _live_attribute("phone_numbers", "Phone Numbers", "phone-number"),
            _live_attribute("keyai_member_id", "Key.ai Member ID", "timestamp"),
        ),
        company_attributes=(_live_attribute("name", "Name", "text"),),
        lifecycle_list=AttioListState(
            list_id="list-123",
            name=ATTIO_SCHEMA.lifecycle.list_name,
            api_slug=ATTIO_SCHEMA.lifecycle.list_api_slug,
            parent_objects=("companies",),
            workspace_access=ATTIO_SCHEMA.lifecycle.workspace_access,
            attributes=(
                _live_attribute("member_status", "Member Status", "text"),
                _live_attribute("joined_at", "Joined At", "text"),
            ),
        ),
    )

    plan = attio_schema.plan_attio_schema_changes(snapshot=snapshot)

    assert {issue.kind for issue in plan.issues} == {
        "missing_required_attribute",
        "attribute_type_mismatch",
        "list_parent_mismatch",
    }
    assert any(issue.api_slug == "company" for issue in plan.issues)
    assert any(issue.api_slug == "keyai_member_id" for issue in plan.issues)
    assert any(issue.api_slug == "joined_at" for issue in plan.issues)


def test_plan_attio_schema_changes_can_archive_extra_custom_attributes() -> None:
    snapshot = AttioWorkspaceSchemaSnapshot(
        people_attributes=(
            _live_attribute("email_addresses", "Email Addresses", "email-address"),
            _live_attribute("name", "Name", "personal-name"),
            _live_attribute("phone_numbers", "Phone Numbers", "phone-number"),
            _live_attribute("company", "Company", "record-reference"),
            _live_attribute("keyai_member_id", "Key.ai Member ID", "text"),
            _live_attribute("linkedin", "LinkedIn URL", "text"),
            _live_attribute(
                "favorite_color", "Favorite Color", "text", is_system=False
            ),
        ),
        company_attributes=(
            _live_attribute("name", "Name", "text"),
            _live_attribute("company_stage", "Company Stage", "text"),
        ),
        lifecycle_list=_lifecycle_list_with_expected_attributes(),
    )

    plan = attio_schema.plan_attio_schema_changes(
        snapshot=snapshot,
        archive_extra_custom_attributes=True,
    )

    assert any(
        action.kind == "archive_attribute" and action.api_slug == "favorite_color"
        for action in plan.actions
    )


def test_apply_attio_schema_plan_creates_list_before_lifecycle_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_calls: list[tuple[str, str]] = []

    def fake_request_json(
        method: str,
        url: str,
        payload: dict[str, object] | None,
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured_calls.append((method, url))
        return {
            "data": {"id": {"list_id": "list-123", "attribute_id": "attribute-123"}}
        }

    monkeypatch.setattr(attio_schema, "_request_json", fake_request_json)
    monkeypatch.setattr(
        attio_schema,
        "export_attio_schema",
        lambda settings=None, list_id=None: AttioWorkspaceSchemaSnapshot(
            people_attributes=(),
            company_attributes=(),
            lifecycle_list=AttioListState(
                list_id="list-123",
                name=ATTIO_SCHEMA.lifecycle.list_name,
                api_slug=ATTIO_SCHEMA.lifecycle.list_api_slug,
                parent_objects=(ATTIO_SCHEMA.lifecycle.parent_object,),
                workspace_access=ATTIO_SCHEMA.lifecycle.workspace_access,
                attributes=(),
            ),
        ),
    )

    plan = attio_schema.plan_attio_schema_changes(
        snapshot=AttioWorkspaceSchemaSnapshot(
            people_attributes=(
                _live_attribute("email_addresses", "Email Addresses", "email-address"),
                _live_attribute("name", "Name", "personal-name"),
                _live_attribute("phone_numbers", "Phone Numbers", "phone-number"),
                _live_attribute("company", "Company", "record-reference"),
            ),
            company_attributes=(_live_attribute("name", "Name", "text"),),
            lifecycle_list=None,
        )
    )

    attio_schema.apply_attio_schema_plan(
        plan=plan,
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
            attio_api_key="attio-token",
        ),
    )

    lifecycle_attribute_urls = [
        url
        for _, url in captured_calls
        if "/lists/funda_founder_lifecycle/attributes" in url
    ]
    assert captured_calls[3] == ("POST", "https://api.attio.com/v2/lists")
    assert lifecycle_attribute_urls
    assert captured_calls.index(
        ("POST", "https://api.attio.com/v2/lists")
    ) < captured_calls.index(("POST", lifecycle_attribute_urls[0]))


def _live_attribute(
    api_slug: str,
    title: str,
    attribute_type: str,
    *,
    is_system: bool = True,
) -> AttioLiveAttribute:
    return AttioLiveAttribute(
        api_slug=api_slug,
        title=title,
        type=attribute_type,
        is_system_attribute=is_system,
    )


def _lifecycle_list_with_expected_attributes() -> AttioListState:
    return AttioListState(
        list_id="list-123",
        name=ATTIO_SCHEMA.lifecycle.list_name,
        api_slug=ATTIO_SCHEMA.lifecycle.list_api_slug,
        parent_objects=(ATTIO_SCHEMA.lifecycle.parent_object,),
        workspace_access=ATTIO_SCHEMA.lifecycle.workspace_access,
        attributes=tuple(
            _live_attribute(
                attribute.api_slug,
                attribute.title,
                attribute.type,
                is_system=False,
            )
            for attribute in ATTIO_SCHEMA.lifecycle.custom_attributes()
        ),
    )
