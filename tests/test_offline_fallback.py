"""What the app does when PocketBase is unreachable.

These paths had never been exercised. They are also the ones most likely to be wrong, because
they only run when something else is already broken.
"""

from conftest import response_with

import app as app_module


def test_index_serves_fallback_items_when_pocketbase_is_down(client, offline):
    response = client.get("/")

    assert response.status_code == 200
    assert b"SANDBOX FALLBACK" in response.data


def test_index_reports_live_when_pocketbase_answers(client, monkeypatch):
    item = {
        "id": "rec1",
        "album": "Kind of Blue",
        "author": "Miles Davis",
        "cdcondition": 9,
        "covercondition": 8,
        "price": 120,
    }
    monkeypatch.setattr(
        app_module.requests, "get", lambda *a, **k: response_with(200, {"items": [item]})
    )

    response = client.get("/")

    assert b"LIVE SYNCED" in response.data
    assert b"Kind of Blue" in response.data


def test_a_failed_fetch_clears_the_cached_url(client, offline):
    """The resolved URL is cached, so a container that moves would otherwise keep a dead address
    until the process restarts. A failed fetch must invalidate it."""
    app_module._cached_internal_url = "http://stale:8090"

    client.get("/")

    assert app_module._cached_internal_url is None


def test_search_filters_by_album_and_artist(client, offline):
    app_module.FALLBACK_ITEMS = [
        {"id": "a", "album": "Kind of Blue", "author": "Miles Davis", "cdcondition": 9,
         "covercondition": 9, "price": 100},
        {"id": "b", "album": "Blue Train", "author": "John Coltrane", "cdcondition": 8,
         "covercondition": 8, "price": 90},
    ]

    assert b"Blue Train" in client.get("/?q=coltrane").data
    assert b"Kind of Blue" not in client.get("/?q=coltrane").data
    # Matching on the album title finds both, since "Blue" appears in each.
    assert b"Kind of Blue" in client.get("/?q=blue").data


def test_search_is_case_insensitive(client, offline):
    app_module.FALLBACK_ITEMS = [
        {"id": "a", "album": "Kind of Blue", "author": "Miles Davis", "cdcondition": 9,
         "covercondition": 9, "price": 100},
    ]

    assert b"Kind of Blue" in client.get("/?q=KIND").data


def test_delete_falls_back_to_local_removal_when_offline(client, offline):
    app_module.FALLBACK_ITEMS = [
        {"id": "gone", "album": "A", "author": "B", "cdcondition": 8, "covercondition": 8,
         "price": 1},
        {"id": "stays", "album": "C", "author": "D", "cdcondition": 8, "covercondition": 8,
         "price": 2},
    ]

    client.get("/delete/gone", headers={"Remote-User": "konrad"})

    assert [item["id"] for item in app_module.FALLBACK_ITEMS] == ["stays"]


def test_delete_of_an_unknown_id_removes_nothing(client, offline):
    before = [dict(item) for item in app_module.FALLBACK_ITEMS]

    client.get("/delete/does-not-exist", headers={"Remote-User": "konrad"})

    assert app_module.FALLBACK_ITEMS == before


def test_add_while_offline_keeps_the_record_in_memory(client, offline):
    before = len(app_module.FALLBACK_ITEMS)

    client.post(
        "/add",
        data={"album": "Blue Train", "author": "John Coltrane", "price": "90"},
        headers={"Remote-User": "konrad"},
    )

    assert len(app_module.FALLBACK_ITEMS) == before + 1
    assert app_module.FALLBACK_ITEMS[0]["album"] == "Blue Train"
