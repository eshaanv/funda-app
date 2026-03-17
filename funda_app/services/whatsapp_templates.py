from funda_app.schemas.whatsapp import WhatsAppTemplateDefinition, WhatsAppTemplateName

FUNDA_SIGNUP_CONFIRMATION_TEMPLATE = WhatsAppTemplateDefinition(
    name=WhatsAppTemplateName.FUNDA_SIGNUP_CONFIRMATION,
    language="en",
    category="UTILITY",
    body_parameter_names=("first_name",),
)

FUNDA_MEMBERSHIP_APPROVED_TEMPLATE = WhatsAppTemplateDefinition(
    name=WhatsAppTemplateName.FUNDA_MEMBERSHIP_APPROVED,
    language="en",
    category="UTILITY",
    body_parameter_names=("first_name",),
)

FUNDA_MEMBERSHIP_REJECTED_TEMPLATE = WhatsAppTemplateDefinition(
    name=WhatsAppTemplateName.FUNDA_MEMBERSHIP_REJECTED,
    language="en",
    category="UTILITY",
    body_parameter_names=("first_name",),
)

FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION_TEMPLATE = WhatsAppTemplateDefinition(
    name=WhatsAppTemplateName.FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION,
    language="en",
    category="UTILITY",
    body_parameter_names=("full_name",),
)

WHATSAPP_TEMPLATE_REGISTRY: dict[WhatsAppTemplateName, WhatsAppTemplateDefinition] = {
    FUNDA_SIGNUP_CONFIRMATION_TEMPLATE.name: FUNDA_SIGNUP_CONFIRMATION_TEMPLATE,
    FUNDA_MEMBERSHIP_APPROVED_TEMPLATE.name: FUNDA_MEMBERSHIP_APPROVED_TEMPLATE,
    FUNDA_MEMBERSHIP_REJECTED_TEMPLATE.name: FUNDA_MEMBERSHIP_REJECTED_TEMPLATE,
    FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION_TEMPLATE.name: FUNDA_NEW_MEMBER_ADMIN_NOTIFICATION_TEMPLATE,
}


def get_whatsapp_template_definition(
    template_name: WhatsAppTemplateName,
) -> WhatsAppTemplateDefinition:
    """
    Returns the WhatsApp template definition for a given template name.

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
