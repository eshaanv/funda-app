from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class WhatsAppTemplateName(StrEnum):
    FUNDA_SIGNUP_CONFIRMATION = "funda_signup_confirmation"
    FUNDA_MEMBERSHIP_APPROVED = "funda_membership_approved"
    FUNDA_MEMBERSHIP_REJECTED = "funda_membership_rejected"


class WhatsAppTemplateDefinition(BaseModel):
    name: WhatsAppTemplateName
    language: str
    category: Literal["UTILITY", "MARKETING", "AUTHENTICATION"]
    body_parameter_names: tuple[str, ...] = ()


class WhatsAppTemplateSendRequest(BaseModel):
    to: str
    template_name: WhatsAppTemplateName
    template_metadata: dict[str, str] = Field(default_factory=dict)


class WhatsAppDispatchResult(BaseModel):
    status: Literal["sent", "skipped"]
    detail: str
    message_id: str | None = None
