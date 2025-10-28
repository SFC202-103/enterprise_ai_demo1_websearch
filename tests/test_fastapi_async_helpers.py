import asyncio
import json
import pytest

from src import fastapi_app as fa
from src import backend_store as bs


def test_push_update_and_store():
    # run the async helper in an asyncio loop to avoid anyio backend issues
    async def _inner():
        # clear any previous
        bs.store._updates.clear()
        res = await fa.push_update({"match_id": "m_async_1", "update": {"x": 1}})
        assert res.get("ok") is True
        val = bs.store.get_update("m_async_1")
        assert val == {"x": 1}

    asyncio.run(_inner())


def test_sse_match_updates_yields_data():
    async def _inner():
        bs.store._updates.clear()
        bs.store.push_update("s1", {"foo": "bar"})
        agen = fa.sse_match_updates("s1")
        # get one item from the async generator
        item = await agen.__anext__()
        assert isinstance(item, str)
        assert item.startswith("data: ")
        payload = json.loads(item[len("data: ") :].strip())
        assert payload == {"foo": "bar"}

    asyncio.run(_inner())


class DummyWS:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def accept(self):
        return None

    async def send_json(self, data):
        self.sent.append(data)
        # raise to exit the loop and trigger close
        raise RuntimeError("stop")

    async def close(self):
        self.closed = True


def test_websocket_match_updates_handles_send_error():
    async def _inner():
        bs.store._updates.clear()
        bs.store.push_update("w1", {"hello": "ws"})
        ws = DummyWS()
        # calling the handler should call send_json and then close on exception
        await fa.websocket_match_updates(ws, "w1")
        assert ws.sent and ws.sent[0] == {"hello": "ws"}
        assert ws.closed is True

    asyncio.run(_inner())


def test_set_tracked_impl_fallback(monkeypatch):
    async def _inner():
        # Force admin to succeed
        monkeypatch.setenv("ADMIN_API_KEY", "admintoken")
        # Ensure db.set_tracked_selection raises so fallback to in-memory occurs
        def bad_set(match_id, team):
            raise RuntimeError("db fail")

        # Patch the function on the real module rather than replacing the module
        import src.db as _dbmod
        monkeypatch.setattr(_dbmod, "set_tracked_selection", bad_set, raising=False)

        res = await fa.set_tracked_impl({"match_id": "t1", "team": "T"}, "admintoken")
        assert res.get("ok") is True
        assert res.get("tracked") is not None

    asyncio.run(_inner())


def test_admin_sync_impl_branches(monkeypatch):
    async def _inner():
        monkeypatch.setenv("ADMIN_API_KEY", "admintoken")

        class Dummy:
            def get_matches(self, game=None):
                return [{"id": "a1"}, {"id": "a2"}]

        monkeypatch.setattr("src.connectors.pandascore_connector.PandaScoreConnector", lambda *a, **k: Dummy())

        res = await fa.admin_sync_impl({"connector": "pandascore"}, "admintoken")
        assert res.get("ok") is True
        assert res.get("pushed") == 2

        # missing connector
        res2 = await fa.admin_sync_impl({}, "admintoken")
        assert res2.get("ok") is False

    asyncio.run(_inner())
