import io
from urllib import error

import pytest

from funda_app.utils import http


class FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body.encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_request_json_retries_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    open_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_urlopen(http_request, timeout: float):
        open_calls.append(http_request.full_url)
        if len(open_calls) == 1:
            raise TimeoutError("The read operation timed out")
        return FakeResponse('{"data": {"id": {"record_id": "person-record-123"}}}')

    monkeypatch.setattr(http.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", sleep_calls.append)

    response = http.request_json(
        method="PUT",
        url="https://api.attio.com/v2/objects/people/records",
        payload={"data": {"values": {"name": "Founder"}}},
        access_token="attio-token",
        timeout_seconds=20.0,
        retry_attempts=3,
    )

    assert response == {"data": {"id": {"record_id": "person-record-123"}}}
    assert len(open_calls) == 2
    assert sleep_calls == [1.0]


def test_request_json_retries_retryable_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    open_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_urlopen(http_request, timeout: float):
        open_calls.append(http_request.full_url)
        if len(open_calls) == 1:
            raise error.HTTPError(
                url=http_request.full_url,
                code=503,
                msg="service unavailable",
                hdrs=None,
                fp=io.BytesIO(b'{"error":"unavailable"}'),
            )
        return FakeResponse('{"data": {"id": {"entry_id": "entry-123"}}}')

    monkeypatch.setattr(http.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", sleep_calls.append)

    response = http.request_json(
        method="PUT",
        url="https://api.attio.com/v2/lists/list-123/entries",
        payload={"data": {"entry_values": {"status": "PENDING"}}},
        access_token="attio-token",
        timeout_seconds=20.0,
        retry_attempts=3,
    )

    assert response == {"data": {"id": {"entry_id": "entry-123"}}}
    assert len(open_calls) == 2
    assert sleep_calls == [1.0]


def test_request_json_does_not_send_body_for_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_request = {}

    def fake_urlopen(http_request, timeout: float):
        captured_request["method"] = http_request.get_method()
        captured_request["data"] = http_request.data
        captured_request["content_type"] = http_request.headers.get("Content-type")
        return FakeResponse('{"data": {"id": {"record_id": "company-record-123"}}}')

    monkeypatch.setattr(http.request, "urlopen", fake_urlopen)

    response = http.request_json(
        method="GET",
        url="https://api.attio.com/v2/objects/companies/records/company-record-123",
        payload={},
        access_token="attio-token",
        timeout_seconds=20.0,
        retry_attempts=3,
    )

    assert response == {"data": {"id": {"record_id": "company-record-123"}}}
    assert captured_request == {
        "method": "GET",
        "data": None,
        "content_type": None,
    }
