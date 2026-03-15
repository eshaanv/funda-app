import json
from collections.abc import Mapping
from urllib import error, parse, request

from funda_app.app_settings import AppSettings, get_app_settings
from funda_app.schemas.crm import (
    ATTIO_SCHEMA,
    AttioAttributeDefinition,
    AttioLiveAttribute,
    AttioListState,
    AttioSchemaAction,
    AttioSchemaIssue,
    AttioSchemaPlan,
    AttioWorkspaceSchemaSnapshot,
)


def export_attio_schema(
    settings: AppSettings | None = None,
    list_id: str | None = None,
) -> AttioWorkspaceSchemaSnapshot:
    """
    Exports the current Attio schema for the Funda-managed targets.

    Args:
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.
        list_id (str | None, optional): Explicit lifecycle list ID override.
            Defaults to None.

    Returns:
        AttioWorkspaceSchemaSnapshot: Live schema snapshot for people,
        companies, and the lifecycle list.

    Raises:
        ValueError: If Attio is not configured.
        urllib.error.HTTPError: If the Attio API rejects the request.
        urllib.error.URLError: If the Attio API is unreachable.
    """
    runtime_settings = settings or get_app_settings()
    _validate_attio_api_key(runtime_settings)

    lifecycle_list = _resolve_lifecycle_list(
        settings=runtime_settings,
        list_id=list_id,
    )

    return AttioWorkspaceSchemaSnapshot(
        people_attributes=_list_attributes(
            target="objects",
            identifier=ATTIO_SCHEMA.person.object_slug,
            settings=runtime_settings,
        ),
        company_attributes=_list_attributes(
            target="objects",
            identifier=ATTIO_SCHEMA.company.object_slug,
            settings=runtime_settings,
        ),
        lifecycle_list=lifecycle_list,
    )


def plan_attio_schema_changes(
    snapshot: AttioWorkspaceSchemaSnapshot,
    archive_extra_custom_attributes: bool = False,
) -> AttioSchemaPlan:
    """
    Builds the Attio schema change plan for the canonical Funda schema.

    Args:
        snapshot (AttioWorkspaceSchemaSnapshot): Live workspace schema.
        archive_extra_custom_attributes (bool, optional): Whether to archive
            extra custom attributes that are not in the canonical schema.
            Defaults to False.

    Returns:
        AttioSchemaPlan: Planned schema actions and blocking issues.
    """
    actions: list[AttioSchemaAction] = []
    issues: list[AttioSchemaIssue] = []

    people_actions, people_issues = _plan_attribute_target(
        target="objects",
        identifier=ATTIO_SCHEMA.person.object_slug,
        live_attributes=snapshot.people_attributes,
        required_attributes=ATTIO_SCHEMA.person.required_attributes(),
        expected_attributes=ATTIO_SCHEMA.person.custom_attributes(),
        archive_extra_custom_attributes=archive_extra_custom_attributes,
    )
    actions.extend(people_actions)
    issues.extend(people_issues)

    company_actions, company_issues = _plan_attribute_target(
        target="objects",
        identifier=ATTIO_SCHEMA.company.object_slug,
        live_attributes=snapshot.company_attributes,
        required_attributes=ATTIO_SCHEMA.company.required_attributes(),
        expected_attributes=ATTIO_SCHEMA.company.custom_attributes(),
        archive_extra_custom_attributes=archive_extra_custom_attributes,
    )
    actions.extend(company_actions)
    issues.extend(company_issues)

    expected_list = ATTIO_SCHEMA.lifecycle.list_definition()
    lifecycle_attributes = (
        snapshot.lifecycle_list.attributes if snapshot.lifecycle_list else ()
    )
    if snapshot.lifecycle_list is None:
        actions.append(
            AttioSchemaAction(
                kind="create_list",
                target="lists",
                identifier=expected_list.api_slug,
                title=expected_list.name,
                payload={"data": expected_list.create_payload()},
            )
        )
    else:
        if expected_list.parent_object not in snapshot.lifecycle_list.parent_objects:
            issues.append(
                AttioSchemaIssue(
                    kind="list_parent_mismatch",
                    target="lists",
                    identifier=snapshot.lifecycle_list.list_id,
                    message=(
                        "Lifecycle list parent object does not match the canonical "
                        f"'{expected_list.parent_object}' parent."
                    ),
                )
            )
        if (
            snapshot.lifecycle_list.name != expected_list.name
            or snapshot.lifecycle_list.api_slug != expected_list.api_slug
            or snapshot.lifecycle_list.workspace_access
            != expected_list.workspace_access
        ):
            actions.append(
                AttioSchemaAction(
                    kind="update_list",
                    target="lists",
                    identifier=snapshot.lifecycle_list.list_id,
                    title=expected_list.name,
                    payload={"data": expected_list.update_payload()},
                )
            )

    lifecycle_actions, lifecycle_issues = _plan_attribute_target(
        target="lists",
        identifier=expected_list.api_slug,
        live_attributes=lifecycle_attributes,
        required_attributes=(),
        expected_attributes=ATTIO_SCHEMA.lifecycle.custom_attributes(),
        archive_extra_custom_attributes=archive_extra_custom_attributes,
    )
    actions.extend(lifecycle_actions)
    issues.extend(lifecycle_issues)

    return AttioSchemaPlan(
        lifecycle_list_id=(
            snapshot.lifecycle_list.list_id
            if snapshot.lifecycle_list is not None
            else None
        ),
        actions=tuple(actions),
        issues=tuple(issues),
    )


def apply_attio_schema_plan(
    plan: AttioSchemaPlan,
    settings: AppSettings | None = None,
) -> AttioWorkspaceSchemaSnapshot:
    """
    Applies a planned Attio schema change set.

    Args:
        plan (AttioSchemaPlan): Planned schema actions to apply.
        settings (AppSettings | None, optional): Runtime settings override.
            Defaults to None.

    Returns:
        AttioWorkspaceSchemaSnapshot: Fresh schema snapshot after apply.

    Raises:
        ValueError: If the plan contains blocking issues or Attio is not configured.
        urllib.error.HTTPError: If the Attio API rejects the request.
        urllib.error.URLError: If the Attio API is unreachable.
    """
    runtime_settings = settings or get_app_settings()
    _validate_attio_api_key(runtime_settings)

    if plan.has_blockers:
        issue_messages = "; ".join(issue.message for issue in plan.issues)
        raise ValueError(f"Attio schema plan has blocking issues: {issue_messages}")

    lifecycle_list_identifier = plan.lifecycle_list_id or ATTIO_SCHEMA.lifecycle.list_api_slug

    for action in plan.actions:
        if action.kind == "create_list":
            response = _request_json(
                method="POST",
                url=f"{runtime_settings.attio_base_url.rstrip('/')}/lists",
                payload=action.payload,
                access_token=runtime_settings.attio_api_key or "",
                timeout_seconds=runtime_settings.attio_timeout_seconds,
            )
            lifecycle_list_identifier = response["data"]["id"]["list_id"]
            continue

        if action.kind == "update_list":
            _request_json(
                method="PATCH",
                url=(
                    f"{runtime_settings.attio_base_url.rstrip('/')}/lists/"
                    f"{action.identifier}"
                ),
                payload=action.payload,
                access_token=runtime_settings.attio_api_key or "",
                timeout_seconds=runtime_settings.attio_timeout_seconds,
            )
            continue

        if action.api_slug is None:
            raise ValueError("Attribute schema actions require an attribute slug")

        target_identifier = action.identifier
        if action.target == "lists" and target_identifier == ATTIO_SCHEMA.lifecycle.list_api_slug:
            target_identifier = lifecycle_list_identifier

        if action.kind == "create_attribute":
            _request_json(
                method="POST",
                url=(
                    f"{runtime_settings.attio_base_url.rstrip('/')}/{action.target}/"
                    f"{target_identifier}/attributes"
                ),
                payload=action.payload,
                access_token=runtime_settings.attio_api_key or "",
                timeout_seconds=runtime_settings.attio_timeout_seconds,
            )
            continue

        if action.kind in {"update_attribute", "archive_attribute"}:
            _request_json(
                method="PATCH",
                url=(
                    f"{runtime_settings.attio_base_url.rstrip('/')}/{action.target}/"
                    f"{target_identifier}/attributes/{action.api_slug}"
                ),
                payload=action.payload,
                access_token=runtime_settings.attio_api_key or "",
                timeout_seconds=runtime_settings.attio_timeout_seconds,
            )

    return export_attio_schema(
        settings=runtime_settings,
        list_id=ATTIO_SCHEMA.lifecycle.list_api_slug,
    )


def _plan_attribute_target(
    target: str,
    identifier: str,
    live_attributes: tuple[AttioLiveAttribute, ...],
    required_attributes: tuple[str, ...],
    expected_attributes: tuple[AttioAttributeDefinition, ...],
    archive_extra_custom_attributes: bool,
) -> tuple[list[AttioSchemaAction], list[AttioSchemaIssue]]:
    live_by_slug = {attribute.api_slug: attribute for attribute in live_attributes}
    actions: list[AttioSchemaAction] = []
    issues: list[AttioSchemaIssue] = []

    for required_slug in required_attributes:
        attribute = live_by_slug.get(required_slug)
        if attribute is None or attribute.is_archived:
            issues.append(
                AttioSchemaIssue(
                    kind="missing_required_attribute",
                    target=target,
                    identifier=identifier,
                    api_slug=required_slug,
                    message=(
                        f"Required Attio attribute '{required_slug}' is missing on "
                        f"{target.rstrip('s')} '{identifier}'."
                    ),
                )
            )

    expected_by_slug = {
        attribute.api_slug: attribute for attribute in expected_attributes
    }
    for expected_attribute in expected_attributes:
        live_attribute = live_by_slug.get(expected_attribute.api_slug)
        if live_attribute is None:
            actions.append(
                AttioSchemaAction(
                    kind="create_attribute",
                    target=target,
                    identifier=identifier,
                    api_slug=expected_attribute.api_slug,
                    title=expected_attribute.title,
                    payload={"data": expected_attribute.create_payload()},
                )
            )
            continue

        if live_attribute.type != expected_attribute.type:
            issues.append(
                AttioSchemaIssue(
                    kind="attribute_type_mismatch",
                    target=target,
                    identifier=identifier,
                    api_slug=expected_attribute.api_slug,
                    message=(
                        f"Attio attribute '{expected_attribute.api_slug}' on "
                        f"{target.rstrip('s')} '{identifier}' has type "
                        f"'{live_attribute.type}', expected '{expected_attribute.type}'."
                    ),
                )
            )
            continue

        if _attribute_needs_update(
            expected_attribute=expected_attribute,
            live_attribute=live_attribute,
        ):
            actions.append(
                AttioSchemaAction(
                    kind="update_attribute",
                    target=target,
                    identifier=identifier,
                    api_slug=expected_attribute.api_slug,
                    title=expected_attribute.title,
                    payload={"data": expected_attribute.update_payload()},
                )
            )

    if archive_extra_custom_attributes:
        for live_attribute in live_attributes:
            if live_attribute.is_system_attribute or live_attribute.is_archived:
                continue

            if live_attribute.api_slug not in expected_by_slug:
                actions.append(
                    AttioSchemaAction(
                        kind="archive_attribute",
                        target=target,
                        identifier=identifier,
                        api_slug=live_attribute.api_slug,
                        title=live_attribute.title,
                        payload={"data": {"is_archived": True}},
                    )
                )

    return actions, issues


def _attribute_needs_update(
    expected_attribute: AttioAttributeDefinition,
    live_attribute: AttioLiveAttribute,
) -> bool:
    return (
        live_attribute.title != expected_attribute.title
        or live_attribute.description != expected_attribute.description
        or live_attribute.is_required != expected_attribute.is_required
        or live_attribute.is_unique != expected_attribute.is_unique
        or live_attribute.is_multiselect != expected_attribute.is_multiselect
        or live_attribute.is_archived
    )


def _resolve_lifecycle_list(
    settings: AppSettings,
    list_id: str | None,
) -> AttioListState | None:
    explicit_identifier = list_id or settings.attio_founder_lifecycle_list_id
    if explicit_identifier is not None and explicit_identifier.strip():
        try:
            return _fetch_list(
                identifier=explicit_identifier,
                settings=settings,
            )
        except error.HTTPError as exc:
            if exc.code != 404:
                raise

    for lifecycle_list in _list_lists(settings):
        if (
            lifecycle_list.api_slug == ATTIO_SCHEMA.lifecycle.list_api_slug
            or lifecycle_list.name == ATTIO_SCHEMA.lifecycle.list_name
        ):
            return _fetch_list(
                identifier=lifecycle_list.list_id,
                settings=settings,
            )

    return None


def _fetch_list(identifier: str, settings: AppSettings) -> AttioListState:
    response = _request_json(
        method="GET",
        url=f"{settings.attio_base_url.rstrip('/')}/lists/{identifier}",
        payload=None,
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return _parse_list_state(
        data=response["data"],
        settings=settings,
    )


def _list_lists(settings: AppSettings) -> tuple[AttioListState, ...]:
    response = _request_json(
        method="GET",
        url=f"{settings.attio_base_url.rstrip('/')}/lists",
        payload=None,
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return tuple(
        _parse_list_state(
            data=list_data,
            settings=settings,
            include_attributes=False,
        )
        for list_data in response["data"]
    )


def _parse_list_state(
    data: Mapping[str, object],
    settings: AppSettings,
    include_attributes: bool = True,
) -> AttioListState:
    list_id = data["id"]["list_id"]
    list_attributes = ()
    if include_attributes:
        list_attributes = _list_attributes(
            target="lists",
            identifier=list_id,
            settings=settings,
        )
    parent_objects = _normalize_parent_objects(data.get("parent_object"))
    return AttioListState(
        list_id=list_id,
        name=data["name"],
        api_slug=data["api_slug"],
        parent_objects=parent_objects,
        workspace_access=data.get("workspace_access"),
        attributes=list_attributes,
    )


def _list_attributes(
    target: str,
    identifier: str,
    settings: AppSettings,
) -> tuple[AttioLiveAttribute, ...]:
    response = _request_json(
        method="GET",
        url=(
            f"{settings.attio_base_url.rstrip('/')}/{target}/{identifier}/attributes"
            f"?{parse.urlencode({'limit': 1000, 'offset': 0})}"
        ),
        payload=None,
        access_token=settings.attio_api_key or "",
        timeout_seconds=settings.attio_timeout_seconds,
    )
    return tuple(_parse_live_attribute(data) for data in response["data"])


def _parse_live_attribute(data: Mapping[str, object]) -> AttioLiveAttribute:
    attribute_id = None
    if "id" in data and "attribute_id" in data["id"]:
        attribute_id = data["id"]["attribute_id"]

    return AttioLiveAttribute(
        attribute_id=attribute_id,
        api_slug=data["api_slug"],
        title=data["title"],
        type=data["type"],
        description=data.get("description"),
        is_system_attribute=data.get("is_system_attribute", False),
        is_required=data.get("is_required", False),
        is_unique=data.get("is_unique", False),
        is_multiselect=data.get("is_multiselect", False),
        is_archived=data.get("is_archived", False),
    )


def _normalize_parent_objects(parent_object: object) -> tuple[str, ...]:
    if isinstance(parent_object, str):
        return (parent_object,)

    if isinstance(parent_object, (list, tuple)):
        return tuple(str(value) for value in parent_object)

    return ()


def _validate_attio_api_key(settings: AppSettings) -> None:
    if settings.attio_api_key is None or not settings.attio_api_key.strip():
        env_var_name = "ATTIO_API_KEY_PROD" if settings.app_env == "prod" else "ATTIO_API_KEY_DEV"
        raise ValueError(f"{env_var_name} is required")


def _request_json(
    method: str,
    url: str,
    payload: dict[str, object] | None,
    access_token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    request_data = None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if payload is not None:
        request_data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(
        url=url,
        data=request_data,
        method=method,
        headers=headers,
    )

    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        raise error.HTTPError(
            url=exc.url,
            code=exc.code,
            msg=response_body or exc.reason,
            hdrs=exc.headers,
            fp=None,
        ) from exc
