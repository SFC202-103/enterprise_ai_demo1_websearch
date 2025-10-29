import os
import pytest
from fastapi.testclient import TestClient  # type: ignore

import src.fastapi_app as fa


@pytest.fixture
def client():
    assert fa.app is not None
    return TestClient(fa.app)


def test_basic_endpoints(client):
    # /api/games
    r = client.get("/api/games")
    assert r.status_code == 200
    d = r.json()
    assert "games" in d

    # /api/tournaments (fixture-backed; may be empty)
    r = client.get("/api/tournaments")
    assert r.status_code == 200

    # /api/matches (falls back to fixture or empty list)
    r = client.get("/api/matches")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_match_not_found(client):
    # choose an unlikely id
    r = client.get("/api/matches/this-id-does-not-exist")
    # FastAPI route returns 404 JSONResponse
    assert r.status_code == 404


def test_admin_push_and_sync(monkeypatch, client):
    # set admin key
    monkeypatch.setenv("ADMIN_API_KEY", "admintoken123")

    # push_update should accept admin header and return ok True
    payload = {"match_id": "mx1", "update": {"type": "sync"}}
    r = client.post("/api/admin/push_update", json=payload, headers={"X-Admin-Token": "admintoken123"})
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # monkeypatch pandascore connector used by admin_sync
    class Dummy:
        def get_matches(self, game=None):
            return [{"id": "x1", "title": "T1"}, {"id": "x2", "title": "T2"}]

    monkeypatch.setattr("src.connectors.pandascore_connector.PandaScoreConnector", lambda *a, **k: Dummy())
    r = client.post("/api/admin/sync_matches", json={"connector": "pandascore"}, headers={"X-Admin-Token": "admintoken123"})
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_tracked_endpoints(monkeypatch, client):
    # set tracked with admin header
    monkeypatch.setenv("ADMIN_API_KEY", "admintoken123")
    r = client.post("/api/tracked", json={"match_id": "track1", "team": "Team A"}, headers={"X-Admin-Token": "admintoken123"})
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # get tracked
    r = client.get("/api/tracked")
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_tracker_status_returns_ok(client):
    r = client.get("/api/tracker/status")
    assert r.status_code == 200
    assert r.json().get("ok") is True
