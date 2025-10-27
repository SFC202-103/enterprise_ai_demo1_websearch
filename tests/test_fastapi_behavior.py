import importlib
import sys
import asyncio
from pathlib import Path


def _load_module_with_fake_fastapi():
    """Install a minimal fake `fastapi` module into sys.modules and import the target module.

    Returns the imported module. The fake FastAPI provides a simple FastAPI
    class and a JSONResponse type used by the module under test.
    """
    class DummyApp:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

        def websocket(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

        def post(self, *args, **kwargs):
            def _dec(f):
                return f

            return _dec

    class DummyWebSocket:
        pass

    class DummyJSONResponse:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.content = content

    fake_fastapi = type(sys)('fastapi')
    fake_fastapi.FastAPI = DummyApp
    fake_fastapi.WebSocket = DummyWebSocket

    fake_responses = type(sys)('fastapi.responses')
    fake_responses.JSONResponse = DummyJSONResponse

    sys.modules['fastapi'] = fake_fastapi
    sys.modules['fastapi.responses'] = fake_responses

    mod = importlib.import_module('src.fastapi_app')
    importlib.reload(mod)
    return mod, DummyJSONResponse


def test_get_match_returns_jsonresponse_when_no_fixture():
    mod, JSONResponse = _load_module_with_fake_fastapi()

    # Ensure fixture is empty and FASTAPI_AVAILABLE is True path is used
    mod._fixture_data = {}
    mod.FASTAPI_AVAILABLE = True

    result = asyncio.run(mod.get_match('nope'))
    # When fixture missing and FastAPI available, we return a JSONResponse-like object
    assert isinstance(result, JSONResponse)
    assert result.status_code == 404


def test_get_matches_and_tournaments_with_fixture():
    # Import module without fake fastapi to use real fixture file
    if 'fastapi' in sys.modules:
        del sys.modules['fastapi']
    if 'fastapi.responses' in sys.modules:
        del sys.modules['fastapi.responses']

    mod = importlib.import_module('src.fastapi_app')
    importlib.reload(mod)

    # Ensure fixture is loaded from tests/fixtures/sample_responses.json
    # If the fixture lacks 'matches' or 'tournaments' keys, the functions should return []
    matches = asyncio.run(mod.get_matches())
    tournaments = asyncio.run(mod.get_tournaments())
    assert isinstance(matches, list)
    assert isinstance(tournaments, list)


def test_websocket_match_updates_calls_send_and_close(monkeypatch):
    # Load module with fake FastAPI to ensure function signature is available
    mod, _ = _load_module_with_fake_fastapi()

    # Create fake websocket that records calls
    class FakeWS:
        def __init__(self):
            self.accepted = False
            self.sent = []
            self.closed = False

        async def accept(self):
            self.accepted = True

        async def send_json(self, data):
            self.sent.append(data)
            # Force an exception after first send to exercise except block and close
            raise RuntimeError("stop")

        async def close(self):
            self.closed = True

    ws = FakeWS()

    # Seed the in-memory store with a single update for match 'm1'
    from src.backend_store import store
    store.push_update('m1', {'score': [1, 0]})

    try:
        asyncio.run(mod.websocket_match_updates(ws, 'm1'))
    except RuntimeError:
        # Expected from our FakeWS.send_json raising - ensure close was called
        pass

    assert ws.accepted is True
    assert ws.sent and ws.sent[0] == {'score': [1, 0]}
    assert ws.closed is True
