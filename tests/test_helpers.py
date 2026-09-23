"""The pure helpers: grading, colours, and the PocketBase URL probe."""

import pytest

import app as app_module
from conftest import response_with


@pytest.mark.parametrize(
    "rating,expected",
    [
        (10, "Mint (M)"),
        (9, "Near Mint (NM)"),
        (8, "Very Good (VG)"),
        (7, "Very Good (VG)"),
        (6, "Good (G)"),
        (5, "Good (G)"),
        (4, "Fair (F)"),
        (3, "Fair (F)"),
        (2, "Poor (P)"),
        (0, "Poor (P)"),
    ],
)
def test_condition_labels_at_every_boundary(rating, expected):
    """Every threshold, because the ladder is a chain of `>=` where an off-by-one is invisible."""
    assert app_module.get_condition_label(rating) == expected


@pytest.mark.parametrize(
    "rating,fragment",
    [(10, "emerald"), (9, "emerald"), (8, "teal"), (7, "teal"), (6, "amber"), (5, "amber"), (4, "rose")],
)
def test_condition_colours_track_the_labels(rating, fragment):
    assert fragment in app_module.get_condition_color(rating)


def test_gradient_is_stable_for_the_same_album():
    first = app_module.get_gradient_style("Kind of Blue", "Miles Davis")
    second = app_module.get_gradient_style("Kind of Blue", "Miles Davis")

    assert first == second


def test_gradient_differs_between_albums():
    blue = app_module.get_gradient_style("Kind of Blue", "Miles Davis")
    train = app_module.get_gradient_style("Blue Train", "John Coltrane")

    assert blue != train


def test_explicit_internal_url_skips_probing(monkeypatch):
    """The override exists so a deployment can state the address outright. If it still probed,
    a wrong guess could win over the operator's own answer."""
    monkeypatch.setenv("POCKETBASE_INTERNAL_URL", "http://pocketbase.internal:8090")

    def fail(*args, **kwargs):
        raise AssertionError("probed despite an explicit URL")

    monkeypatch.setattr(app_module.requests, "get", fail)

    assert app_module.get_pocketbase_internal_url() == "http://pocketbase.internal:8090"


def test_the_first_responding_candidate_wins(monkeypatch):
    attempted = []

    def probe(url, **kwargs):
        attempted.append(url)
        if "pocketbase:" in url:
            return response_with(200)
        import requests

        raise requests.exceptions.ConnectionError("nope")

    monkeypatch.setattr(app_module.requests, "get", probe)

    assert "pocketbase:" in app_module.get_pocketbase_internal_url()


def test_a_404_still_counts_as_a_live_server(monkeypatch):
    """A running PocketBase with no such collection answers 404. That is still a server, and
    treating it as unreachable would send the app into fallback while the database is fine."""
    monkeypatch.setattr(app_module.requests, "get", lambda *a, **k: response_with(404))

    assert app_module.get_pocketbase_internal_url() is not None


def test_the_result_is_cached(monkeypatch):
    calls = []
    monkeypatch.setattr(
        app_module.requests, "get", lambda url, **k: calls.append(url) or response_with(200)
    )

    first = app_module.get_pocketbase_internal_url()
    before = len(calls)
    second = app_module.get_pocketbase_internal_url()

    assert first == second
    assert len(calls) == before, "probed again instead of using the cache"


def test_everything_unreachable_falls_back_to_the_configured_url(monkeypatch, offline):
    assert app_module.get_pocketbase_internal_url() == app_module.POCKETBASE_URL
