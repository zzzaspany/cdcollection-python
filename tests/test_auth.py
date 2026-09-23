"""The app authenticates nobody itself — it trusts headers a forward-auth proxy sets.

That makes these the most important tests here: they pin down exactly which headers grant a write,
and that no header means no write.
"""

import app as app_module
from conftest import response_with


def test_no_headers_means_nobody(client):
    with app_module.app.test_request_context("/"):
        assert app_module.get_auth_user() is None


def test_each_accepted_header_identifies_the_caller(client):
    for header in ("Remote-User", "X-Webauth-User", "X-Forwarded-User"):
        with app_module.app.test_request_context("/", headers={header: "konrad"}):
            assert app_module.get_auth_user() == "konrad", header


def test_remote_user_wins_over_the_others(client):
    headers = {"Remote-User": "first", "X-Webauth-User": "second", "X-Forwarded-User": "third"}
    with app_module.app.test_request_context("/", headers=headers):
        assert app_module.get_auth_user() == "first"


def test_surrounding_whitespace_is_stripped(client):
    with app_module.app.test_request_context("/", headers={"Remote-User": "  konrad  "}):
        assert app_module.get_auth_user() == "konrad"


def test_an_empty_header_is_not_an_identity(client):
    """An empty header must not authenticate: a proxy that forwards a blank value should not
    accidentally grant write access."""
    with app_module.app.test_request_context("/", headers={"Remote-User": ""}):
        assert app_module.get_auth_user() is None


def test_mock_auth_user_overrides_everything(client, monkeypatch):
    """MOCK_AUTH_USER bypasses authentication entirely. It exists so the app is usable without a
    proxy in front of it; this test is here so that behaviour is explicit rather than discovered."""
    monkeypatch.setenv("MOCK_AUTH_USER", "developer")
    with app_module.app.test_request_context("/", headers={"Remote-User": "konrad"}):
        assert app_module.get_auth_user() == "developer"


def test_adding_without_an_identity_is_refused(client, monkeypatch):
    """The write must not reach PocketBase at all — not merely be reported as failed."""
    calls = []
    monkeypatch.setattr(app_module.requests, "post", lambda *a, **k: calls.append(a) or response_with(200))

    response = client.post("/add", data={"album": "Kind of Blue", "author": "Miles Davis"})

    assert response.status_code == 302
    assert calls == []


def test_deleting_without_an_identity_is_refused(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_module.requests, "delete", lambda *a, **k: calls.append(a) or response_with(204)
    )
    before = list(app_module.FALLBACK_ITEMS)

    response = client.get("/delete/rec123")

    assert response.status_code == 302
    assert calls == []
    assert app_module.FALLBACK_ITEMS == before


def test_deleting_with_an_identity_reaches_pocketbase(client, monkeypatch):
    calls = []

    def record(url, **kwargs):
        calls.append(url)
        return response_with(204)

    monkeypatch.setattr(app_module.requests, "delete", record)
    monkeypatch.setattr(app_module.requests, "get", lambda *a, **k: response_with(200, {"items": []}))

    response = client.get("/delete/rec123", headers={"Remote-User": "konrad"})

    assert response.status_code == 302
    assert len(calls) == 1
    assert calls[0].endswith("/records/rec123")
