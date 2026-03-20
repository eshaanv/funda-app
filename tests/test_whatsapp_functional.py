import os
from uuid import uuid4

import pytest
from pydantic import ValidationError

from funda_app.schemas.webhooks import MemberJoinedWebhookPayload
from funda_app.schemas.whatsapp import WhatsAppTemplateName
from funda_app.services import keyai_webhooks, whatsapp
from funda_app.services.whatsapp_templates import get_whatsapp_template_definition
from funda_app.app_settings import get_app_settings

LIVE_RECIPIENT_PHONE = "19256400611"
LIVE_TEMPLATE_FIRST_NAME = "Eshaan"


def _live_whatsapp_test_enabled() -> bool:
    return os.environ.get("RUN_LIVE_WHATSAPP_TESTS") == "1"


def _has_live_whatsapp_settings() -> bool:
    try:
        get_app_settings.cache_clear()
        get_app_settings()
    except ValidationError:
        return False

    return True


@pytest.mark.skipif(
    not _live_whatsapp_test_enabled(),
    reason="Set RUN_LIVE_WHATSAPP_TESTS=1 to run the live WhatsApp functional test.",
)
@pytest.mark.skipif(
    not _has_live_whatsapp_settings(),
    reason="Live WhatsApp settings are not configured.",
)
def test_member_joined_live_whatsapp_dispatch() -> None:
    payload = MemberJoinedWebhookPayload.model_validate(
        {
            "event": "member.joined",
            "member": {
                "id": "14b8d602-1eee-11f1-b904-0242ac14000a",
                "email": "eshaan@example.com",
                "phone": "",
                "fullName": "Eshaan Vipani",
                "lastName": "Vipani",
                "firstName": LIVE_TEMPLATE_FIRST_NAME,
            },
            "status": {
                "new": "PENDING",
                "old": None,
            },
            "eventId": str(uuid4()),
            "version": 1,
            "community": {
                "id": "b382558c-1ebd-11f1-b36c-0242ac14000a",
                "name": "funda",
            },
            "questions": [
                {
                    "answer": "Eshaan",
                    "question": "What is your first name?",
                },
                {
                    "answer": LIVE_RECIPIENT_PHONE,
                    "question": "What is your whatsapp number?",
                    "semantic_key": "whatsapp_number",
                },
            ],
            "occurredAt": "2026-03-14T15:05:32.436Z",
        }
    )
    send_request = keyai_webhooks.build_keyai_whatsapp_send_request(payload)

    assert send_request is not None
    assert send_request.to == LIVE_RECIPIENT_PHONE
    assert send_request.template_name == WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION
    assert send_request.template_metadata == {
        "first_name": LIVE_TEMPLATE_FIRST_NAME,
    }

    graph_api_payload = whatsapp._build_graph_api_payload(
        send_request=send_request,
        template=get_whatsapp_template_definition(send_request.template_name),
    )

    assert graph_api_payload == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": LIVE_RECIPIENT_PHONE,
        "type": "template",
        "template": {
            "name": "funda_signup_confirmation",
            "language": {
                "code": "en",
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": LIVE_TEMPLATE_FIRST_NAME,
                        }
                    ],
                }
            ],
        },
    }

    result = whatsapp.send_whatsapp_template_message(send_request)

    assert result.status == "sent"
    assert result.message_id is not None
