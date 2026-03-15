from datetime import datetime

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


class AttioCompanySchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    object_slug: str = "companies"
    name_attribute: str = "name"
    stage_attribute: str = "company_stage"


class AttioLifecycleSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    parent_object: str = "people"
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
