from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, Field


class MemberWebhookEvent(StrEnum):
    MEMBER_JOINED = "member.joined"
    MEMBER_APPROVED = "member.approved"
    MEMBER_REJECTED = "member.rejected"
    MEMBER_REMOVED = "member.removed"
    MEMBER_LEFT = "member.left"


class MemberStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"
    LEFT = "LEFT"


class CommunityPayload(BaseModel):
    id: str
    name: str


class MemberPayload(BaseModel):
    id: str
    email: str
    phone: str | None = None
    fullName: str
    lastName: str | None = None
    firstName: str
    companyName: str | None = None
    linkedinUrl: str | None = None
    companyStage: str | None = None


class MemberQuestionPayload(BaseModel):
    question: str
    answer: str
    semantic_key: str


class BaseMemberStatusPayload(BaseModel):
    old: MemberStatus | None = None
    new: MemberStatus


class MemberJoinedStatusPayload(BaseMemberStatusPayload):
    old: None = None
    new: Literal[MemberStatus.PENDING] = MemberStatus.PENDING


class MemberApprovedStatusPayload(BaseMemberStatusPayload):
    old: Literal[MemberStatus.PENDING]
    new: Literal[MemberStatus.APPROVED] = MemberStatus.APPROVED


class MemberRejectedStatusPayload(BaseMemberStatusPayload):
    old: Literal[MemberStatus.PENDING]
    new: Literal[MemberStatus.REJECTED] = MemberStatus.REJECTED


class MemberRemovedStatusPayload(BaseMemberStatusPayload):
    old: Literal[MemberStatus.APPROVED]
    new: Literal[MemberStatus.REMOVED] = MemberStatus.REMOVED


class MemberLeftStatusPayload(BaseMemberStatusPayload):
    old: Literal[MemberStatus.APPROVED]
    new: Literal[MemberStatus.LEFT] = MemberStatus.LEFT


class BaseMemberWebhookPayload(BaseModel):
    event: MemberWebhookEvent
    version: int
    eventId: str
    occurredAt: datetime
    community: CommunityPayload
    member: MemberPayload
    status: BaseMemberStatusPayload
    questions: list[MemberQuestionPayload] | None = None


class MemberJoinedWebhookPayload(BaseMemberWebhookPayload):
    event: Literal[MemberWebhookEvent.MEMBER_JOINED] = MemberWebhookEvent.MEMBER_JOINED
    status: MemberJoinedStatusPayload
    questions: list[MemberQuestionPayload] | None = None


class MemberApprovedWebhookPayload(BaseMemberWebhookPayload):
    event: Literal[MemberWebhookEvent.MEMBER_APPROVED] = (
        MemberWebhookEvent.MEMBER_APPROVED
    )
    status: MemberApprovedStatusPayload


class MemberRejectedWebhookPayload(BaseMemberWebhookPayload):
    event: Literal[MemberWebhookEvent.MEMBER_REJECTED] = (
        MemberWebhookEvent.MEMBER_REJECTED
    )
    status: MemberRejectedStatusPayload


class MemberRemovedWebhookPayload(BaseMemberWebhookPayload):
    event: Literal[MemberWebhookEvent.MEMBER_REMOVED] = (
        MemberWebhookEvent.MEMBER_REMOVED
    )
    status: MemberRemovedStatusPayload


class MemberLeftWebhookPayload(BaseMemberWebhookPayload):
    event: Literal[MemberWebhookEvent.MEMBER_LEFT] = MemberWebhookEvent.MEMBER_LEFT
    status: MemberLeftStatusPayload


MemberWebhookPayload: TypeAlias = Annotated[
    MemberJoinedWebhookPayload
    | MemberApprovedWebhookPayload
    | MemberRejectedWebhookPayload
    | MemberRemovedWebhookPayload
    | MemberLeftWebhookPayload,
    Field(discriminator="event"),
]


class WebhookAcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    event: MemberWebhookEvent
    user_id: str
