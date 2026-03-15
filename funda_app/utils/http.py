"""
Shared HTTP utilities for outbound API requests.
"""

import json
from urllib import error, request


def request_json(
    method: str,
    url: str,
    payload: dict[str, object],
    access_token: str,
    timeout_seconds: float,
) -> dict[str, object]:
    """
    Sends a JSON request with Bearer auth and returns the response as parsed JSON.

    Args:
        method: HTTP method (e.g. GET, POST, PUT, PATCH).
        url: Request URL.
        payload: JSON-serializable body (ignored for GET; use {} if none).
        access_token: Bearer token for the Authorization header.
        timeout_seconds: Request timeout in seconds.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        urllib.error.HTTPError: When the server returns a non-2xx status.
        urllib.error.URLError: When the request cannot be completed.
    """
    request_body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=request_body,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8")
        raise error.HTTPError(
            url=exc.url,
            code=exc.code,
            msg=response_body or exc.reason,
            hdrs=exc.headers,
            fp=None,
        ) from exc
