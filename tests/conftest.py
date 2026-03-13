import pytest
from fastapi.testclient import TestClient

from funda_app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())
