from funda_app.schemas.whatsapp import WhatsAppTemplateDefinition, WhatsAppTemplateName

FUNDA_SIGNUP_CONFIRMATION_TEMPLATE = WhatsAppTemplateDefinition(
    name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
    language="en",
    category="UTILITY",
    body_parameter_names=("first_name",),
)

WHATSAPP_TEMPLATE_REGISTRY: dict[WhatsAppTemplateName, WhatsAppTemplateDefinition] = {
    FUNDA_SIGNUP_CONFIRMATION_TEMPLATE.name: FUNDA_SIGNUP_CONFIRMATION_TEMPLATE,
}


def get_whatsapp_template(
    template_name: WhatsAppTemplateName,
) -> WhatsAppTemplateDefinition:
    """
    Fetches a WhatsApp template definition from the registry.

    Args:
        template_name (WhatsAppTemplateName): The approved template name.

    Returns:
        WhatsAppTemplateDefinition: The configured template definition.

    Raises:
        ValueError: If the template name is not registered.
    """
    try:
        return WHATSAPP_TEMPLATE_REGISTRY[template_name]
    except KeyError as exc:
        raise ValueError(f"Unknown WhatsApp template: {template_name}") from exc
