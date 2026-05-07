from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator


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
    linkedinUrl: str | None = None


class MemberQuestionType(StrEnum):
    MULTIPLE_CHOICE_SINGLE = "multiple_choice_single"
    MULTIPLE_CHOICE_MULTI = "multiple_choice_multi"
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    EMAIL = "email"
    NUMBER = "number"
    DATE = "date"
    PHONE_NUMBER = "phone_number"
    WEBSITE_URL = "website_url"
    COUNTRY = "country"


QuestionAnswer: TypeAlias = str | list[str] | None


class MemberQuestionPayload(BaseModel):
    type: MemberQuestionType
    question: str
    answer: QuestionAnswer
    semantic_key: str

    @model_validator(mode="after")
    def validate_answer_shape(self) -> "MemberQuestionPayload":
        """
        Validates that the answer shape matches the question type.

        Returns:
            MemberQuestionPayload: The validated question payload.

        Raises:
            ValueError: If the answer shape does not match the question type.
        """
        list_types = {
            MemberQuestionType.MULTIPLE_CHOICE_SINGLE,
            MemberQuestionType.MULTIPLE_CHOICE_MULTI,
        }

        if self.answer is None:
            return self

        if self.type in list_types:
            if not isinstance(self.answer, list):
                raise ValueError(
                    "answer must be a string array for multiple choice question types"
                )
        elif not isinstance(self.answer, str):
            raise ValueError(
                "answer must be a string for non-multiple-choice question types"
            )

        return self


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
