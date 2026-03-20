"""
Shared HTTP utilities for outbound API requests.
"""

import json
import logging
import time
from urllib import error, request

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def request_json(
    method: str,
    url: str,
    payload: dict[str, object],
    access_token: str,
    timeout_seconds: float,
    retry_attempts: int = 1,
) -> dict[str, object]:
    """
    Sends a JSON request with Bearer auth and returns the response as parsed JSON.

    Args:
        method: HTTP method (e.g. GET, POST, PUT, PATCH).
        url: Request URL.
        payload: JSON-serializable body (ignored for GET; use {} if none).
        access_token: Bearer token for the Authorization header.
        timeout_seconds: Request timeout in seconds.
        retry_attempts: Number of transient-failure attempts to make.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        urllib.error.HTTPError: When the server returns a non-2xx status.
        urllib.error.URLError: When the request cannot be completed.
    """
    request_body = None
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if method.upper() != "GET":
        request_body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    http_request = request.Request(
        url=url,
        data=request_body,
        method=method,
        headers=headers,
    )

    for attempt in range(1, retry_attempts + 1):
        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            response_body = exc.read().decode("utf-8")
            wrapped_exc = error.HTTPError(
                url=exc.url,
                code=exc.code,
                msg=(
                    f"{method} {url} failed with status {exc.code}: "
                    f"{response_body or exc.reason}"
                ),
                hdrs=exc.headers,
                fp=None,
            )
            if exc.code not in RETRYABLE_STATUS_CODES or attempt == retry_attempts:
                raise wrapped_exc from exc
            logger.warning(
                "Retrying HTTP request: method=%s url=%s attempt=%s max_attempts=%s reason=%s",
                method,
                url,
                attempt + 1,
                retry_attempts,
                f"http_{exc.code}",
            )
        except (error.URLError, TimeoutError) as exc:
            if attempt == retry_attempts:
                raise
            logger.warning(
                "Retrying HTTP request: method=%s url=%s attempt=%s max_attempts=%s reason=%s",
                method,
                url,
                attempt + 1,
                retry_attempts,
                str(exc),
            )

        time.sleep(float(attempt))

    raise RuntimeError("HTTP request retry loop exited unexpectedly")
