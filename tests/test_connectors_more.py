import time
import httpx
import pytest


class _FakeResp:
    def __init__(self, json_data, status_code=200, headers=None):
        self._json = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("status", request=None, response=self)

    def json(self):
        return self._json


def test_pandascore_retry_after_nonint(monkeypatch):
    calls = {"n": 0}

    def fake_sleep(sec):
        # no-op to keep test fast
        return None

    class FakeClient:
        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _FakeResp([], status_code=429, headers={"Retry-After": "abc"})
            return _FakeResp([{"id": 101, "name": "X vs Y", "opponents": []}])

    monkeypatch.setattr(time, "sleep", fake_sleep)
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: FakeClient())

    # Import the connector module directly to avoid executing package-level
    # imports in `src/__init__.py` which pull in optional heavy deps.
    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "src" / "connectors" / "pandascore_connector.py"
    spec = importlib.util.spec_from_file_location("pandascore_connector_for_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    PandaScoreConnector = mod.PandaScoreConnector

    conn = PandaScoreConnector(token="t", max_retries=1)
    got = conn.get_matches()
    assert got and got[0]["id"] == 101


def test_pandascore_retry_after_nonzero(monkeypatch):
    calls = {"n": 0, "slept": []}

    def fake_sleep(sec):
        calls["slept"].append(sec)

    class FakeClient:
        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _FakeResp([], status_code=429, headers={"Retry-After": "1"})
            return _FakeResp([{"id": 102, "name": "A vs B", "opponents": []}])

    monkeypatch.setattr(time, "sleep", fake_sleep)
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: FakeClient())

    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "src" / "connectors" / "pandascore_connector.py"
    spec = importlib.util.spec_from_file_location("pandascore_connector_for_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    PandaScoreConnector = mod.PandaScoreConnector

    conn = PandaScoreConnector(token="t", max_retries=1)
    got = conn.get_matches()
    assert got and got[0]["id"] == 102
    assert calls["slept"] == [1]


def test_riot_retry_after_nonint(monkeypatch):
    calls = {"n": 0}

    monkeypatch.setattr(time, "sleep", lambda _: None)

    class FakeClient:
        def get(self, *args, **kwargs):
            if calls["n"] == 0:
                calls["n"] += 1
                return _FakeResp([], status_code=429, headers={"Retry-After": "nope"})
            return _FakeResp([{"id": "r101", "gameName": "R1"}])

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: FakeClient())

    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "src" / "connectors" / "riot_connector.py"
    spec = importlib.util.spec_from_file_location("riot_connector_for_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    RiotConnector = mod.RiotConnector

    conn = RiotConnector(token="r", max_retries=1)
    got = conn.get_matches()
    assert got and got[0]["id"] == "r101"


def test_pandascore_429_exhaust_no_retry(monkeypatch):
    # When max_retries=0 and the first response is 429 with non-int Retry-After,
    # the connector should raise the underlying HTTPStatusError.
    class FakeClient:
        def get(self, *args, **kwargs):
            return _FakeResp([], status_code=429, headers={"Retry-After": "x"})

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: FakeClient())

    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "src" / "connectors" / "pandascore_connector.py"
    spec = importlib.util.spec_from_file_location("pandascore_connector_for_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    PandaScoreConnector = mod.PandaScoreConnector

    with pytest.raises(httpx.HTTPStatusError):
        PandaScoreConnector(token="t", max_retries=0).get_matches()


def test_riot_429_exhaust_no_retry(monkeypatch):
    class FakeClient:
        def get(self, *args, **kwargs):
            return _FakeResp([], status_code=429, headers={"Retry-After": "x"})

    monkeypatch.setattr(httpx, "Client", lambda *a, **k: FakeClient())

    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parent.parent / "src" / "connectors" / "riot_connector.py"
    spec = importlib.util.spec_from_file_location("riot_connector_for_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    RiotConnector = mod.RiotConnector

    with pytest.raises(httpx.HTTPStatusError):
        RiotConnector(token="r", max_retries=0).get_matches()
