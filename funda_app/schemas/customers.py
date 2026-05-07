from datetime import datetime

from pydantic import BaseModel, Field

from funda_app.schemas.crm import AttioCompanySyncPayload, AttioPersonSyncPayload
from funda_app.schemas.webhooks import MemberStatus, MemberWebhookEvent


class KeyAICustomerSyncRequest(BaseModel):
    """
    Represents a normalized Key.ai customer sync request for Firestore.

    Args:
        event (MemberWebhookEvent): Source Key.ai member event.
        event_id (str): Unique Key.ai webhook event ID.
        occurred_at (datetime): When the source event occurred.
        community_id (str): Key.ai community ID.
        community_name (str): Key.ai community name.
        previous_status (MemberStatus | None): Previous member status.
        member_status (MemberStatus): Current member status.
        person (AttioPersonSyncPayload): Normalized person fields.
        company (AttioCompanySyncPayload | None, optional): Normalized company
            fields. Defaults to None.
        question_answers (dict[str, str], optional): Canonical question answers.
            Defaults to an empty dict.
        keyai_questions (list[dict[str, object]], optional): Raw Key.ai questions
            with canonical keys attached. Defaults to an empty list.
    """

    event: MemberWebhookEvent
    event_id: str
    occurred_at: datetime
    community_id: str
    community_name: str
    previous_status: MemberStatus | None
    member_status: MemberStatus
    person: AttioPersonSyncPayload
    company: AttioCompanySyncPayload | None = None
    question_answers: dict[str, str] = Field(default_factory=dict)
    keyai_questions: list[dict[str, object]] = Field(default_factory=list)


class KeyAICustomerSyncResult(BaseModel):
    """
    Represents the Firestore customer sync result.

    Args:
        status (str): Sync status.
        customer_document_id (str): Customer document ID.
        event_document_id (str): Event history document ID.
    """

    status: str
    customer_document_id: str
    event_document_id: str
