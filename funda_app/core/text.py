import re


def sanitize_whatsapp_text(value: str) -> str:
    """
    Sanitizes freeform text for WhatsApp template parameters.

    Args:
        value (str): Raw text to sanitize.

    Returns:
        str: Single-line text with collapsed whitespace.
    """
    sanitized = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", sanitized).strip()
