"""Background sync worker that periodically fetches matches from connectors
and persists them using `src.db.save_matches`.

This worker is intentionally simple for the prototype: it runs in a
separate thread and polls every SYNC_INTERVAL seconds. Use environment
variables to configure connectors and DB.
"""
from __future__ import annotations

import os
import threading
import time
from typing import List

from src.db import init_db, save_matches


def _load_connectors() -> List[str]:
    val = os.getenv("SYNC_CONNECTORS", "pandascore")
    return [c.strip() for c in val.split(",") if c.strip()]


def run_once() -> int:
    """Run a single sync across configured connectors.

    Returns number of matches saved.
    """
    total = 0
    connectors = _load_connectors()
    for c in connectors:
        try:
            if c == "pandascore":
                from src.connectors.pandascore_connector import PandaScoreConnector

                conn = PandaScoreConnector()
                matches = conn.get_matches()
            elif c == "riot":
                from src.connectors.riot_connector import RiotConnector

                conn = RiotConnector()
                matches = conn.get_matches()
            else:
                matches = []
        except Exception:
            matches = []

        if matches:
            saved = save_matches(matches)
            total += saved
    return total


class SyncWorker:
    def __init__(self, interval: int = 60):
        self.interval = int(os.getenv("SYNC_INTERVAL", str(interval)))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        init_db()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                run_once()
            except Exception:
                pass
            # wait interval or until stopped
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)


_global_worker: SyncWorker | None = None


def start_worker(interval: int = 60) -> SyncWorker:
    global _global_worker
    if _global_worker is None:
        _global_worker = SyncWorker(interval=interval)
        _global_worker.start()
    return _global_worker


def stop_worker() -> None:
    global _global_worker
    if _global_worker is not None:
        _global_worker.stop()
        _global_worker = None
