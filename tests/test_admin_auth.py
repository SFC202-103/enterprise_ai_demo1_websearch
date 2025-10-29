import sys
import json
import asyncio

import pytest

from fastapi.testclient import TestClient  # type: ignore


def test_push_update_header_auth(monkeypatch):
    # Ensure admin key is required
    monkeypatch.setenv("ADMIN_API_KEY", "s3cr3t")

    from src.fastapi_app import app

    client = TestClient(app)
    res = client.post("/api/admin/push_update", json={"match_id": "m1", "update": {"score": 1}})
    assert res.status_code == 401

    res2 = client.post("/api/admin/push_update", headers={"X-Admin-Token": "s3cr3t"}, json={"match_id": "m1", "update": {"score": 1}})
    assert res2.status_code == 200
    assert res2.json().get("ok") is True


def test_admin_sync_header_auth(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "sync-key")

    # Provide a fake PandaScore connector so the sync doesn't call the network
    sample = [{"id": "mx1", "title": "A v B"}]

    class FakePanda:
        def __init__(self, *args, **kwargs):
            pass

        def get_matches(self, *args, **kwargs):
            return sample

    monkeypatch.setitem(sys.modules, "src.connectors.pandascore_connector", type("M", (), {"PandaScoreConnector": FakePanda}))

    from src.fastapi_app import app

    client = TestClient(app)
    res = client.post("/api/admin/sync_matches", json={"connector": "pandascore"})
    assert res.status_code == 401

    res2 = client.post("/api/admin/sync_matches", headers={"X-Admin-Token": "sync-key"}, json={"connector": "pandascore"})
    assert res2.status_code == 200
    assert res2.json().get("ok") is True
    assert res2.json().get("pushed") == 1
