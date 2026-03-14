import json
from urllib import error, request

from funda_app.schemas.whatsapp import (
    WhatsAppDispatchResult,
    WhatsAppTemplateDefinition,
    WhatsAppTemplateSendRequest,
)
from funda_app.services.whatsapp_templates import get_whatsapp_template
from funda_app.app_settings import AppSettings, get_app_settings


def send_whatsapp_template_message(
    send_request: WhatsAppTemplateSendRequest,
    settings: AppSettings | None = None,
) -> WhatsAppDispatchResult:
    """
    Sends an approved WhatsApp template message through the Graph API.

    Args:
        send_request (WhatsAppTemplateSendRequest): Template send request.
        settings (AppSettings | None, optional): Explicit runtime settings.
            Defaults to None.

    Returns:
        WhatsAppDispatchResult: The accepted provider response details.

    Raises:
        RuntimeError: If the Graph API rejects the request.
        ValueError: If the template metadata does not match the registry.
    """
    runtime_settings = settings or get_app_settings()
    template = get_whatsapp_template(send_request.template_name)
    payload = _build_graph_api_payload(send_request, template)
    url = (
        f"{runtime_settings.whatsapp_base_url.rstrip('/')}/"
        f"{runtime_settings.whatsapp_api_version}/"
        f"{runtime_settings.whatsapp_phone_number_id}/messages"
    )
    response = _post_json(
        url=url,
        payload=payload,
        access_token=runtime_settings.whatsapp_access_token,
        timeout_seconds=runtime_settings.whatsapp_timeout_seconds,
    )
    message_id = None

    if response.get("messages"):
        message_id = response["messages"][0].get("id")

    return WhatsAppDispatchResult(
        status="sent",
        detail="WhatsApp template accepted by Graph API.",
        message_id=message_id,
    )


def _build_graph_api_payload(
    send_request: WhatsAppTemplateSendRequest,
    template: WhatsAppTemplateDefinition,
) -> dict[str, object]:
    body_parameters = _build_body_parameters(send_request, template)
    template_payload: dict[str, object] = {
        "name": template.name,
        "language": {
            "code": template.language,
        },
    }

    if body_parameters:
        template_payload["components"] = [
            {
                "type": "body",
                "parameters": body_parameters,
            }
        ]

    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": send_request.to,
        "type": "template",
        "template": template_payload,
    }


def _build_body_parameters(
    send_request: WhatsAppTemplateSendRequest,
    template: WhatsAppTemplateDefinition,
) -> list[dict[str, str]]:
    required_names = template.body_parameter_names
    provided_names = set(send_request.template_metadata)
    missing_names = [
        parameter_name
        for parameter_name in required_names
        if parameter_name not in send_request.template_metadata
    ]
    unexpected_names = sorted(provided_names.difference(required_names))

    if missing_names or unexpected_names:
        message_parts: list[str] = []

        if missing_names:
            message_parts.append(
                f"missing metadata: {', '.join(sorted(missing_names))}"
            )

        if unexpected_names:
            message_parts.append(
                f"unexpected metadata: {', '.join(unexpected_names)}"
            )

        raise ValueError(
            f"Template metadata mismatch for {template.name}: {'; '.join(message_parts)}"
        )

    return [
        {
            "type": "text",
            "text": send_request.template_metadata[parameter_name],
        }
        for parameter_name in required_names
    ]


def _post_json(
    url: str,
    payload: dict[str, object],
    access_token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(
            f"WhatsApp Graph API request failed with status {exc.code}: {detail}"
        ) from exc
