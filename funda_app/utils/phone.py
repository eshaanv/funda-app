"""
Phone number normalization and related utilities.
"""


def normalize_phone_number(raw_value: str | None) -> str | None:
    """
    Normalizes a phone number into E.164-like format.

    Args:
        raw_value (str | None): Source phone number.

    Returns:
        str | None: Normalized phone number, or None when the source is empty.
    """
    if raw_value is None or not raw_value.strip():
        return None

    stripped_value = raw_value.strip()
    digits = "".join(character for character in stripped_value if character.isdigit())
    if not digits:
        return None

    if stripped_value.startswith("+"):
        return f"+{digits}"

    if len(digits) == 10:
        return f"+1{digits}"

    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    return f"+{digits}"


def get_country_code(phone_number: str) -> str | None:
    """
    Returns the country code for a phone number when determinable.

    Args:
        phone_number: E.164-like phone number (e.g. +1...).

    Returns:
        ISO country code (e.g. "US") or None if not recognized.
    """
    if phone_number.startswith("+1"):
        return "US"

    return None
