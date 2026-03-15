from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from funda_app.schemas.webhooks import MemberStatus, MemberWebhookEvent


class AttioPersonSyncPayload(BaseModel):
    keyai_member_id: str
    email: str
    full_name: str
    first_name: str
    last_name: str
    phone: str | None = None
    linkedin_url: str | None = None


class AttioCompanySyncPayload(BaseModel):
    name: str
    stage: str | None = None


class AttioLifecycleSyncRequest(BaseModel):
    event: MemberWebhookEvent
    event_id: str
    occurred_at: datetime
    community_id: str
    community_name: str
    member_status: MemberStatus
    person: AttioPersonSyncPayload
    company: AttioCompanySyncPayload | None = None


class AttioSyncResult(BaseModel):
    status: str
    person_record_id: str
    lifecycle_entry_id: str
    company_record_id: str | None = None


class AttioAttributeDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    api_slug: str
    type: str = "text"
    config: dict[str, object] = Field(default_factory=dict)
    description: str | None = None
    is_required: bool = False
    is_unique: bool = False
    is_multiselect: bool = False

    def create_payload(self) -> dict[str, object]:
        """
        Builds the Attio attribute creation payload.

        Returns:
            dict[str, object]: JSON payload for the Attio create-attribute API.
        """
        payload: dict[str, object] = {
            "title": self.title,
            "api_slug": self.api_slug,
            "type": self.type,
            "config": self.config,
            "is_required": self.is_required,
            "is_unique": self.is_unique,
            "is_multiselect": self.is_multiselect,
        }
        if self.description is not None:
            payload["description"] = self.description

        return payload

    def update_payload(self) -> dict[str, object]:
        """
        Builds the Attio attribute update payload.

        Returns:
            dict[str, object]: JSON payload for the Attio update-attribute API.
        """
        payload: dict[str, object] = {
            "title": self.title,
            "api_slug": self.api_slug,
            "config": self.config,
            "is_required": self.is_required,
            "is_unique": self.is_unique,
            "is_archived": False,
        }
        if self.description is not None:
            payload["description"] = self.description

        return payload


class AttioListDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    api_slug: str
    parent_object: str
    workspace_access: str = "read-and-write"

    def create_payload(self) -> dict[str, object]:
        """
        Builds the Attio list creation payload.

        Returns:
            dict[str, object]: JSON payload for the Attio create-list API.
        """
        return {
            "name": self.name,
            "api_slug": self.api_slug,
            "parent_object": self.parent_object,
            "workspace_access": self.workspace_access,
        }

    def update_payload(self) -> dict[str, object]:
        """
        Builds the Attio list update payload.

        Returns:
            dict[str, object]: JSON payload for the Attio update-list API.
        """
        return {
            "name": self.name,
            "api_slug": self.api_slug,
            "workspace_access": self.workspace_access,
        }


class AttioLiveAttribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    attribute_id: str | None = None
    api_slug: str
    title: str
    type: str
    description: str | None = None
    is_system_attribute: bool = False
    is_required: bool = False
    is_unique: bool = False
    is_multiselect: bool = False
    is_archived: bool = False


class AttioListState(BaseModel):
    model_config = ConfigDict(frozen=True)

    list_id: str
    name: str
    api_slug: str
    parent_objects: tuple[str, ...] = ()
    workspace_access: str | None = None
    attributes: tuple[AttioLiveAttribute, ...] = ()


class AttioWorkspaceSchemaSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    people_attributes: tuple[AttioLiveAttribute, ...]
    company_attributes: tuple[AttioLiveAttribute, ...]
    lifecycle_list: AttioListState | None = None


class AttioSchemaAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[
        "create_list",
        "update_list",
        "create_attribute",
        "update_attribute",
        "archive_attribute",
    ]
    target: Literal["objects", "lists"]
    identifier: str
    api_slug: str | None = None
    title: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class AttioSchemaIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[
        "missing_required_attribute",
        "attribute_type_mismatch",
        "list_parent_mismatch",
    ]
    target: Literal["objects", "lists"]
    identifier: str
    api_slug: str | None = None
    message: str


class AttioSchemaPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    lifecycle_list_id: str | None = None
    actions: tuple[AttioSchemaAction, ...] = ()
    issues: tuple[AttioSchemaIssue, ...] = ()

    @property
    def is_clean(self) -> bool:
        """
        Indicates whether the schema already matches the canonical contract.

        Returns:
            bool: True when there are no pending changes or issues.
        """
        return not self.actions and not self.issues

    @property
    def has_blockers(self) -> bool:
        """
        Indicates whether the plan contains schema problems that cannot be
        auto-applied safely.

        Returns:
            bool: True when the plan contains blocking issues.
        """
        return bool(self.issues)


class AttioPersonSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_slug: str = "people"
    matching_attribute: str = "email_addresses"
    email_attribute: str = "email_addresses"
    name_attribute: str = "name"
    phone_attribute: str = "phone_numbers"
    external_id_attribute: str = "keyai_member_id"
    linkedin_attribute: str = "linkedin"
    company_relationship_attribute: str = "company"

    def required_attributes(self) -> tuple[str, ...]:
        """
        Returns the required system attributes for Attio person sync.

        Returns:
            tuple[str, ...]: System attribute slugs that must exist.
        """
        return (
            self.email_attribute,
            self.name_attribute,
            self.phone_attribute,
            self.company_relationship_attribute,
        )

    def custom_attributes(self) -> tuple[AttioAttributeDefinition, ...]:
        """
        Returns the Funda-managed custom person attributes.

        Returns:
            tuple[AttioAttributeDefinition, ...]: Person attribute definitions.
        """
        return (
            AttioAttributeDefinition(
                title="Key.ai Member ID",
                api_slug=self.external_id_attribute,
                description="Stable member identifier from Key.ai.",
            ),
            AttioAttributeDefinition(
                title="LinkedIn URL",
                api_slug=self.linkedin_attribute,
                description="LinkedIn profile URL from Key.ai.",
            ),
        )


class AttioCompanySchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_slug: str = "companies"
    name_attribute: str = "name"
    stage_attribute: str = "company_stage"

    def required_attributes(self) -> tuple[str, ...]:
        """
        Returns the required system attributes for Attio company sync.

        Returns:
            tuple[str, ...]: System attribute slugs that must exist.
        """
        return (self.name_attribute,)

    def custom_attributes(self) -> tuple[AttioAttributeDefinition, ...]:
        """
        Returns the Funda-managed custom company attributes.

        Returns:
            tuple[AttioAttributeDefinition, ...]: Company attribute definitions.
        """
        return (
            AttioAttributeDefinition(
                title="Company Stage",
                api_slug=self.stage_attribute,
                description="Funding or company stage supplied by Key.ai.",
            ),
        )


class AttioLifecycleSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    list_name: str = "Funda Founder Lifecycle"
    list_api_slug: str = "funda_founder_lifecycle"
    parent_object: str = "people"
    workspace_access: str = "read-and-write"
    status_attribute: str = "member_status"
    last_event_attribute: str = "last_keyai_event"
    last_event_id_attribute: str = "last_keyai_event_id"
    last_event_at_attribute: str = "last_keyai_event_at"
    community_name_attribute: str = "community_name"
    community_id_attribute: str = "keyai_community_id"
    joined_at_attribute: str = "joined_at"
    approved_at_attribute: str = "approved_at"
    rejected_at_attribute: str = "rejected_at"
    removed_at_attribute: str = "removed_at"
    left_at_attribute: str = "left_at"

    def list_definition(self) -> AttioListDefinition:
        """
        Returns the canonical Attio lifecycle list definition.

        Returns:
            AttioListDefinition: Lifecycle list definition.
        """
        return AttioListDefinition(
            name=self.list_name,
            api_slug=self.list_api_slug,
            parent_object=self.parent_object,
            workspace_access=self.workspace_access,
        )

    def custom_attributes(self) -> tuple[AttioAttributeDefinition, ...]:
        """
        Returns the Funda-managed lifecycle list attributes.

        Returns:
            tuple[AttioAttributeDefinition, ...]: Lifecycle attribute definitions.
        """
        return (
            AttioAttributeDefinition(
                title="Member Status",
                api_slug=self.status_attribute,
                description="Current Key.ai member lifecycle status.",
            ),
            AttioAttributeDefinition(
                title="Last Key.ai Event",
                api_slug=self.last_event_attribute,
                description="Most recent Key.ai lifecycle event name.",
            ),
            AttioAttributeDefinition(
                title="Last Key.ai Event ID",
                api_slug=self.last_event_id_attribute,
                description="Most recent Key.ai lifecycle event identifier.",
            ),
            AttioAttributeDefinition(
                title="Last Key.ai Event At",
                api_slug=self.last_event_at_attribute,
                type="timestamp",
                description="Timestamp of the most recent Key.ai lifecycle event.",
            ),
            AttioAttributeDefinition(
                title="Community Name",
                api_slug=self.community_name_attribute,
                description="Current Key.ai community name.",
            ),
            AttioAttributeDefinition(
                title="Key.ai Community ID",
                api_slug=self.community_id_attribute,
                description="Stable Key.ai community identifier.",
            ),
            AttioAttributeDefinition(
                title="Joined At",
                api_slug=self.joined_at_attribute,
                type="timestamp",
                description="Timestamp of the member.joined event.",
            ),
            AttioAttributeDefinition(
                title="Approved At",
                api_slug=self.approved_at_attribute,
                type="timestamp",
                description="Timestamp of the member.approved event.",
            ),
            AttioAttributeDefinition(
                title="Rejected At",
                api_slug=self.rejected_at_attribute,
                type="timestamp",
                description="Timestamp of the member.rejected event.",
            ),
            AttioAttributeDefinition(
                title="Removed At",
                api_slug=self.removed_at_attribute,
                type="timestamp",
                description="Timestamp of the member.removed event.",
            ),
            AttioAttributeDefinition(
                title="Left At",
                api_slug=self.left_at_attribute,
                type="timestamp",
                description="Timestamp of the member.left event.",
            ),
        )

    def timestamp_attribute_for_event(self, event: MemberWebhookEvent) -> str:
        """
        Returns the lifecycle timestamp attribute slug for a member event.

        Args:
            event (MemberWebhookEvent): Source Key.ai member event.

        Returns:
            str: Attio lifecycle timestamp attribute slug.
        """
        if event == MemberWebhookEvent.MEMBER_JOINED:
            return self.joined_at_attribute
        if event == MemberWebhookEvent.MEMBER_APPROVED:
            return self.approved_at_attribute
        if event == MemberWebhookEvent.MEMBER_REJECTED:
            return self.rejected_at_attribute
        if event == MemberWebhookEvent.MEMBER_REMOVED:
            return self.removed_at_attribute

        return self.left_at_attribute


class AttioSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    person: AttioPersonSchema = Field(default_factory=AttioPersonSchema)
    company: AttioCompanySchema = Field(default_factory=AttioCompanySchema)
    lifecycle: AttioLifecycleSchema = Field(default_factory=AttioLifecycleSchema)


ATTIO_SCHEMA = AttioSchema()
