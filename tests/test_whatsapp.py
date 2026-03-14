import pytest
from pydantic import ValidationError

from funda_app.schemas.whatsapp import WhatsAppTemplateName, WhatsAppTemplateSendRequest
from funda_app.services import whatsapp
from funda_app.settings import AppSettings


def test_send_whatsapp_template_message_posts_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post_json(
        url: str,
        payload: dict[str, object],
        access_token: str,
        timeout_seconds: float,
    ) -> dict[str, object]:
        captured["url"] = url
        captured["payload"] = payload
        captured["access_token"] = access_token
        captured["timeout_seconds"] = timeout_seconds
        return {"messages": [{"id": "wamid.123"}]}

    monkeypatch.setattr(whatsapp, "_post_json", fake_post_json)

    result = whatsapp.send_whatsapp_template_message(
        send_request=WhatsAppTemplateSendRequest(
            to="19256400611",
            template_name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
            template_metadata={"first_name": "Eshaan"},
        ),
        settings=AppSettings(
            whatsapp_access_token="token",
            whatsapp_phone_number_id="1029270380269800",
        ),
    )

    assert captured["url"] == "https://graph.facebook.com/v25.0/1029270380269800/messages"
    assert captured["payload"] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "19256400611",
        "type": "template",
        "template": {
            "name": "funda_signup_confirmation",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": "Eshaan",
                        }
                    ],
                }
            ],
        },
    }
    assert captured["access_token"] == "token"
    assert captured["timeout_seconds"] == 10.0
    assert result.status == "sent"
    assert result.message_id == "wamid.123"


def test_send_whatsapp_template_message_requires_all_metadata() -> None:
    with pytest.raises(
        ValueError,
        match="missing metadata: first_name",
    ):
        whatsapp.send_whatsapp_template_message(
            send_request=WhatsAppTemplateSendRequest(
                to="19256400611",
                template_name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
            ),
            settings=AppSettings(
                whatsapp_access_token="token",
                whatsapp_phone_number_id="1029270380269800",
            ),
        )


def test_send_whatsapp_template_message_rejects_unknown_metadata() -> None:
    with pytest.raises(
        ValueError,
        match="unexpected metadata: full_name",
    ):
        whatsapp.send_whatsapp_template_message(
            send_request=WhatsAppTemplateSendRequest(
                to="19256400611",
                template_name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
                template_metadata={
                    "first_name": "Eshaan",
                    "full_name": "Eshaan Vipani",
                },
            ),
            settings=AppSettings(
                whatsapp_access_token="token",
                whatsapp_phone_number_id="1029270380269800",
            ),
        )


def test_send_request_rejects_unknown_template_name() -> None:
    with pytest.raises(ValidationError, match="Input should be"):
        WhatsAppTemplateSendRequest(
            to="19256400611",
            template_name="unknown_template",
        )
