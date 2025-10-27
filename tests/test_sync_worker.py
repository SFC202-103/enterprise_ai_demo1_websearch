import os
import sys
import time
from types import SimpleNamespace


def test__load_connectors_and_unknown(monkeypatch):
    # set multiple connectors including an unknown one
    monkeypatch.setenv("SYNC_CONNECTORS", "pandascore, riot , unknown")
    from src.sync_worker import _load_connectors

    lst = _load_connectors()
    assert "pandascore" in lst
    assert "riot" in lst
    assert "unknown" in lst


def test_run_once_handles_multiple_connectors_and_exceptions(monkeypatch):
    # Fake pandascore returns one match
    sample_p = [{"id": "p1", "title": "p1"}]

    class FakePanda:
        def __init__(self, *a, **k):
            pass

        def get_matches(self, *a, **k):
            return sample_p

    # Fake riot raises on get_matches
    class FakeRiot:
        def __init__(self, *a, **k):
            pass

        def get_matches(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setitem(
        sys.modules,
        "src.connectors.pandascore_connector",
        SimpleNamespace(PandaScoreConnector=FakePanda),
    )
    monkeypatch.setitem(
        sys.modules,
        "src.connectors.riot_connector",
        SimpleNamespace(RiotConnector=FakeRiot),
    )

    monkeypatch.setenv("SYNC_CONNECTORS", "pandascore,riot,missing")

    from src.sync_worker import run_once

    saved = run_once()
    # panda produced 1 and riot raised; unknown produced 0
    assert saved >= 1


def test_syncworker_loop_calls_run_once(monkeypatch):
    # Replace run_once with a counter to ensure the loop executes
    called = {"n": 0}

    def fake_run_once():
        called["n"] += 1
        return 0

    monkeypatch.setattr("src.sync_worker.run_once", fake_run_once)

    from src.sync_worker import SyncWorker

    # use integer interval (0 allowed) because SyncWorker casts env/default to int
    w = SyncWorker(interval=0)
    try:
        w.start()
        # give the worker a small amount of time to run a few iterations
        time.sleep(0.05)
    finally:
        w.stop()

    assert called["n"] >= 1


def test_start_stop_worker_wrappers(monkeypatch):
    # ensure the module-level helpers start and stop the global worker
    monkeypatch.setattr("src.sync_worker.run_once", lambda: 0)

    from src.sync_worker import start_worker, stop_worker

    w = start_worker(interval=0)
    assert w is not None
    # allow a brief moment and then stop
    time.sleep(0.02)
    stop_worker()


def test_syncworker_loop_handles_exceptions(monkeypatch):
    # ensure exceptions raised by run_once inside the loop are swallowed
    def raise_once():
        raise RuntimeError("fail")

    monkeypatch.setattr("src.sync_worker.run_once", raise_once)
    from src.sync_worker import SyncWorker

    w = SyncWorker(interval=0)
    try:
        w.start()
        time.sleep(0.02)
    finally:
        w.stop()
