from typing import Any, Literal

from pydantic import BaseModel

JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None
KeyAIEventName = Literal["keyai.users", "keyai.user_status"]


class KeyAIWebhookEvent(BaseModel):
    event: KeyAIEventName
    payload: JSONValue
    user_id: str | None = None


class WebhookAcceptedResponse(BaseModel):
    status: Literal["accepted"] = "accepted"
    event: KeyAIEventName
    user_id: str | None = None


class WhatsAppDispatchResult(BaseModel):
    status: Literal["placeholder"] = "placeholder"
    detail: str
