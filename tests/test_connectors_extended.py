import time
from types import SimpleNamespace

import httpx
import pytest


def _make_fake_response(json_data, status_code=200, headers=None):
    class FakeResp:
        def __init__(self):
            self._json = json_data
            self.status_code = status_code
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                # emulate httpx.HTTPStatusError
                raise httpx.HTTPStatusError("status", request=None, response=self)

        def json(self):
            return self._json

    return FakeResp()


def test_pandascore_retry_after(monkeypatch):
    # Simulate a 429 response first with Retry-After=0 then a success
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_fake_response([], status_code=429, headers={"Retry-After": "0"})
            return _make_fake_response([
                {"id": 7, "name": "A vs B", "opponents": []}
            ])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="t", max_retries=1)
    got = conn.get_matches()
    assert isinstance(got, list)


def test_pandascore_normalization_missing_fields(monkeypatch):
    sample = [{"id": 9}]

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return _make_fake_response(sample)

    monkeypatch.setattr(httpx, "Client", FakeClient)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="t")
    got = conn.get_matches()
    assert got[0]["title"].startswith("match-")
    assert got[0]["teams"] == []


def test_riot_retry_after(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_fake_response([], status_code=429, headers={"Retry-After": "0"})
            return _make_fake_response([{"id": "r9", "gameName": "G"}])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    from src.connectors.riot_connector import RiotConnector

    conn = RiotConnector(token="r", max_retries=1)
    got = conn.get_matches()
    assert isinstance(got, list)
