import asyncio
from types import SimpleNamespace

import httpx
import pytest


def _make_fake_response(json_data):
    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return json_data

    return FakeResp()


def test_pandascore_connector_with_mock(monkeypatch):
    # Prepare a fake httpx.Client whose .get returns a predictable payload
    sample = [
        {
            "id": 1,
            "name": "Team A vs Team B",
            "opponents": [{"opponent": {"id": 10, "name": "Team A"}}, {"opponent": {"id": 20, "name": "Team B"}}],
            "scheduled_at": "2025-10-24T12:00:00Z",
        }
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return _make_fake_response(sample)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="fake-token")
    got = conn.get_matches()
    assert isinstance(got, list)
    assert got and got[0]["id"] == 1
    assert "teams" in got[0] and len(got[0]["teams"]) == 2


def test_riot_connector_with_mock(monkeypatch):
    sample = [
        {"id": "r1", "gameName": "Riot Match 1", "teams": [{"id": "t1", "name": "Alpha"}]}
    ]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return _make_fake_response(sample)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    from src.connectors.riot_connector import RiotConnector

    conn = RiotConnector(token="fake-riot")
    got = conn.get_matches()
    assert isinstance(got, list)
    assert got and got[0]["id"] == "r1"
    assert got[0]["title"] == "Riot Match 1"


def test_admin_sync_pushes_into_store(monkeypatch):
    # Replace PandaScoreConnector with a fake that returns sample matches
    sample = [{"id": "m123", "title": "S1 vs S2"}, {"id": "m456", "title": "S3 vs S4"}]

    class FakePanda:
        def __init__(self, *args, **kwargs):
            pass

        def get_matches(self, *args, **kwargs):
            return sample

    monkeypatch.setitem(__import__("sys").modules, "src.connectors.pandascore_connector", SimpleNamespace(PandaScoreConnector=FakePanda))

    # Import the admin_sync coroutine and the store
    from src.fastapi_app import admin_sync
    from src.backend_store import store

    # Clear any existing updates
    store._updates.clear()

    result = asyncio.run(admin_sync({"connector": "pandascore"}))
    assert result.get("ok") is True
    assert result.get("pushed") == 2

    # Pop the two pushed updates
    u1 = store.get_update("m123")
    u2 = store.get_update("m456")
    assert u1 and u1.get("type") == "sync"
    assert u2 and u2.get("type") == "sync"


def test_connectors_raise_when_no_token(monkeypatch):
    # Ensure no relevant env variables exist
    monkeypatch.delenv("PANDASCORE_TOKEN", raising=False)
    monkeypatch.delenv("RIOT_API_TOKEN", raising=False)

    from src.connectors.pandascore_connector import PandaScoreConnector
    from src.connectors.riot_connector import RiotConnector

    with pytest.raises(ValueError):
        PandaScoreConnector(token=None).get_matches()

    with pytest.raises(ValueError):
        RiotConnector(token=None).get_matches()


def test_connector_internal_methods(monkeypatch):
    # Ensure _client_instance and _headers branches are exercised for both connectors
    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._created = True

        def get(self, *args, **kwargs):
            return _make_fake_response([])

    monkeypatch.setattr(httpx, "Client", FakeClient)

    from src.connectors.pandascore_connector import PandaScoreConnector
    from src.connectors.riot_connector import RiotConnector

    pc = PandaScoreConnector(token="t")
    inst = pc._client_instance()
    assert isinstance(inst, FakeClient)
    hdrs = pc._headers()
    assert "Authorization" in hdrs and "Bearer" in hdrs["Authorization"]

    rc = RiotConnector(token="r")
    inst2 = rc._client_instance()
    assert isinstance(inst2, FakeClient)
    hdrs2 = rc._headers()
    assert "X-Riot-Token" in hdrs2 and hdrs2["X-Riot-Token"] == "r"


def test_connectors_retry_and_raise(monkeypatch):
    # Simulate httpx.Client.get always raising so connector exhausts retries
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            raise RuntimeError("network")

    monkeypatch.setattr(httpx, "Client", BrokenClient)

    from src.connectors.pandascore_connector import PandaScoreConnector
    from src.connectors.riot_connector import RiotConnector

    with pytest.raises(RuntimeError):
        PandaScoreConnector(token="t", max_retries=1).get_matches()

    with pytest.raises(RuntimeError):
        RiotConnector(token="r", max_retries=1).get_matches()
