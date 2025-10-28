import asyncio
import os

import pytest

from src import fastapi_app as fa


def test_get_games_and_tournaments():
    # run simple async helpers
    g = asyncio.run(fa.get_games())
    assert isinstance(g, dict) and "games" in g

    t = asyncio.run(fa.get_tournaments())
    assert isinstance(t, list)


def test_list_db_tournaments_returns_list():
    # Should return empty list when DB has no tournaments (safe to call)
    res = asyncio.run(fa.list_db_tournaments())
    assert isinstance(res, list)


def test_get_matches_fallback_to_fixture():
    # Ensure no PANDASCORE_TOKEN set so fallback to fixture path is used
    monkey_env = os.environ.pop("PANDASCORE_TOKEN", None)
    try:
        res = asyncio.run(fa.get_matches())
        assert isinstance(res, list)
    finally:
        if monkey_env is not None:
            os.environ["PANDASCORE_TOKEN"] = monkey_env


def test_get_live_matches_provider_branches(monkeypatch):
    sample_ps = [{"id": "pm1", "status": "running"}]
    sample_riot = [{"id": "rm1", "status": "scheduled", "scheduled_time": "2099-01-01T00:00:00Z"}]

    class PS:
        def get_matches(self, game=None):
            return sample_ps

    class RI:
        def get_matches(self, game=None):
            return sample_riot

    monkeypatch.setattr("src.connectors.pandascore_connector.PandaScoreConnector", lambda *a, **k: PS())
    out = asyncio.run(fa.get_live_matches(provider="pandascore", status="live"))
    assert isinstance(out, list) and any(m["id"] == "pm1" for m in out)

    monkeypatch.setattr("src.connectors.riot_connector.RiotConnector", lambda *a, **k: RI())
    out2 = asyncio.run(fa.get_live_matches(provider="riot", status="upcoming"))
    assert isinstance(out2, list) and any(m["id"] == "rm1" for m in out2)


def test_get_match_found_and_notfound():
    # pick an ID from fixtures if present
    fx = fa._fixture_data.get("matches", [])
    if fx:
        mid = fx[0].get("id")
        r = asyncio.run(fa.get_match(str(mid)))
        assert isinstance(r, dict)

    r2 = asyncio.run(fa.get_match("unlikely-id-xyz"))
    # may return a JSONResponse (FastAPI) or a dict fallback
    from fastapi.responses import JSONResponse
    if isinstance(r2, JSONResponse):
        assert r2.status_code == 404
    else:
        assert isinstance(r2, dict)


def test_admin_sync_endpoint_uses_connector(monkeypatch):
    # monkeypatch pandascore to return matches
    class PS2:
        def get_matches(self, game=None):
            return [{"id": "a1"}]

    monkeypatch.setattr("src.connectors.pandascore_connector.PandaScoreConnector", lambda *a, **k: PS2())
    res = asyncio.run(fa.admin_sync_impl({"connector": "pandascore"}, "fake"))
    assert isinstance(res, dict)
