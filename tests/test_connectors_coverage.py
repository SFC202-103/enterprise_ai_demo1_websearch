import time
import httpx
import pytest


def _make_resp(json_data=None, status_code=200, headers=None):
    class Resp:
        def __init__(self):
            self._json = json_data or []
            self.status_code = status_code
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=None, response=self)

        def json(self):
            return self._json

    return Resp()


def test_pandascore_retry_after_nonzero(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_resp([], status_code=429, headers={"Retry-After": "1"})
            return _make_resp([{"id": 101, "name": "A v B", "opponents": []}])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.pandascore_connector import PandaScoreConnector

    c = PandaScoreConnector(token="t", max_retries=2)
    out = c.get_matches()
    assert isinstance(out, list)
    assert out and out[0]["id"] == 101


def test_pandascore_retry_after_nonint_then_success(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                # Retry-After non-integer should be treated as 0 and fallthrough
                return _make_resp([], status_code=429, headers={"Retry-After": "abc"})
            return _make_resp([{"id": 202, "name": "C v D", "opponents": []}])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.pandascore_connector import PandaScoreConnector

    c = PandaScoreConnector(token="t", max_retries=2)
    out = c.get_matches()
    assert out and out[0]["id"] == 202


def test_pandascore_raises_after_retries(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            raise RuntimeError("net")

    monkeypatch.setattr(httpx, "Client", BrokenClient)
    from src.connectors.pandascore_connector import PandaScoreConnector

    with pytest.raises(RuntimeError):
        PandaScoreConnector(token="t", max_retries=1).get_matches()


def test_riot_retry_after_nonint_then_success(monkeypatch):
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_resp([], status_code=429, headers={"Retry-After": "xyz"})
            return _make_resp([{"id": "r202", "gameName": "G"}])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.riot_connector import RiotConnector

    c = RiotConnector(token="r", max_retries=2)
    out = c.get_matches()
    assert out and out[0]["id"] == "r202"
