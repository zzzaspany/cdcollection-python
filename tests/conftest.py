import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_module  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_module_state(monkeypatch):
    """`FALLBACK_ITEMS` and the resolved PocketBase URL are module globals that the routes mutate.

    Without this every test would inherit whatever the previous one left behind, and the suite
    would pass or fail depending on the order it happened to run in.
    """
    original_items = list(app_module.FALLBACK_ITEMS)
    app_module.clear_pocketbase_cache()
    monkeypatch.delenv("MOCK_AUTH_USER", raising=False)
    monkeypatch.delenv("POCKETBASE_INTERNAL_URL", raising=False)
    yield
    app_module.FALLBACK_ITEMS = original_items
    app_module.clear_pocketbase_cache()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def offline(monkeypatch):
    """Every outbound call fails, as though PocketBase were not running."""
    import requests

    def refuse(*args, **kwargs):
        raise requests.exceptions.ConnectionError("PocketBase is down")

    monkeypatch.setattr(app_module.requests, "get", refuse)
    monkeypatch.setattr(app_module.requests, "post", refuse)
    monkeypatch.setattr(app_module.requests, "delete", refuse)


def response_with(status_code, json_body=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = json_body if json_body is not None else {}
    return response
