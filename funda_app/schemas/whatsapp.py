from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from funda_app.schemas.webhooks import MemberWebhookEvent


class WhatsAppTemplateName(StrEnum):
    FUNDA_SIGNUP_CONFIRMATION = "funda_signup_confirmation"
    FUNDA_MEMBERSHIP_APPROVED = "funda_membership_approved1"
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


def whatsapp_template_name_for_event(
    event: MemberWebhookEvent,
) -> WhatsAppTemplateName | None:
    """Returns the WhatsApp template name for a Key.ai member webhook event, or None if unsupported."""
    if event == MemberWebhookEvent.MEMBER_JOINED:
        return WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION
    if event == MemberWebhookEvent.MEMBER_APPROVED:
        return WhatsAppTemplateName.FUNDA_MEMBERSHIP_APPROVED
    if event == MemberWebhookEvent.MEMBER_REJECTED:
        return WhatsAppTemplateName.FUNDA_MEMBERSHIP_REJECTED
    return None
