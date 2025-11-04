import time
import httpx
import pytest


def _make_resp(json_data, status_code=200, headers=None):
    class R:
        def __init__(self):
            self._json = json_data
            self.status_code = status_code
            self.headers = headers or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("err", request=None, response=self)

        def json(self):
            return self._json

    return R()


def test_pandascore_retry_after_non_integer(monkeypatch):
    # Retry-After non-integer (e.g., date string) should be treated as 0 and fallthrough
    calls = {"n": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *a, **k):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_resp([], status_code=429, headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})
            return _make_resp([{"id": 11, "name": "x"}])

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="t", max_retries=1)
    got = conn.get_matches()
    assert got and got[0]["id"] == 11


def test_pandascore_5xx_retries_then_raises(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            self.calls = 0

        def get(self, *a, **k):
            self.calls += 1
            return _make_resp([], status_code=500)

    monkeypatch.setattr(httpx, "Client", BrokenClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.pandascore_connector import PandaScoreConnector

    with pytest.raises(httpx.HTTPStatusError):
        PandaScoreConnector(token="t", max_retries=1).get_matches()


def test_riot_retry_after_nonzero_sleep(monkeypatch):
    # If Retry-After is non-zero, connector should sleep that amount then retry
    calls = {"n": 0}
    slept = {"t": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *a, **k):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_resp([], status_code=429, headers={"Retry-After": "1"})
            return _make_resp([{"id": "r100", "gameName": "G"}])

    def fake_sleep(s):
        slept["t"] += s

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    from src.connectors.riot_connector import RiotConnector

    conn = RiotConnector(token="r", max_retries=1)
    got = conn.get_matches()
    assert slept["t"] == 1
    assert got and got[0]["id"] == "r100"


def test_riot_5xx_raises(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *a, **k):
            return _make_resp([], status_code=502)

    monkeypatch.setattr(httpx, "Client", BrokenClient)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    from src.connectors.riot_connector import RiotConnector

    with pytest.raises(httpx.HTTPStatusError):
        RiotConnector(token="r", max_retries=1).get_matches()


def test_pandascore_retry_after_nonzero_sleep(monkeypatch):
    calls = {"n": 0}
    slept = {"t": 0}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *a, **k):
            if calls["n"] == 0:
                calls["n"] += 1
                return _make_resp([], status_code=429, headers={"Retry-After": "2"})
            return _make_resp([{"id": 12, "name": "y"}])

    def fake_sleep(s):
        slept["t"] += s

    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="t", max_retries=1)
    got = conn.get_matches()
    assert slept["t"] == 2
    assert got and got[0]["id"] == 12


def test_pandascore_no_token_raises(monkeypatch):
    # Ensure env var absent and no token passed
    monkeypatch.delenv("PANDASCORE_TOKEN", raising=False)
    from src.connectors.pandascore_connector import PandaScoreConnector

    with pytest.raises(ValueError):
        PandaScoreConnector(token=None).get_matches()


def test_pandascore_game_param_sets_filter(monkeypatch):
    # Ensure the `game` parameter branch is executed
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, url, headers=None, params=None):
            # assert that the filter param was set by the connector (updated to filter[videogame])
            assert params and "filter[videogame]" in params
            return _make_resp([{"id": 21, "name": "G1"}])

    monkeypatch.setattr(httpx, "Client", FakeClient)

    from src.connectors.pandascore_connector import PandaScoreConnector

    conn = PandaScoreConnector(token="t")
    got = conn.get_matches(game="valorant")
    assert got and got[0]["id"] == 21
