"""
Domain normalization utilities.
"""

from urllib.parse import urlparse


def normalize_domain(raw_value: str | None) -> str | None:
    """
    Normalizes a website URL/domain to a bare domain suitable for Attio `domains`.

    Examples:
        "https://www.wellsfargo.com/" -> "wellsfargo.com"
        "www.newco.com" -> "newco.com"
        "newco.com" -> "newco.com"
    """
    if raw_value is None or not raw_value.strip():
        return None

    value = raw_value.strip()
    parsed = urlparse(value if "://" in value else f"https://{value}")
    hostname = parsed.hostname
    if hostname is None:
        return None

    lowered = hostname.strip().lower()
    if lowered.startswith("www."):
        lowered = lowered[4:]

    return lowered or None
