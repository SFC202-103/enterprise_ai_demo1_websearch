"""Simple seeder that pushes demo match updates into the in-memory store.

Run this script during development to simulate live match events that clients
subscribing to the websocket or SSE endpoint will receive.

Usage:
  python scripts/run_seeder.py --match-id m1 --interval 2 --count 10

The script is intentionally small and synchronous to be easy to run in dev.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timedelta

from src.backend_store import store


def _make_score_update(seq: int) -> dict:
    return {
        "type": "score",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "seq": seq,
        "home": random.randint(0, 10),
        "away": random.randint(0, 10),
    }


def _make_event_update(seq: int) -> dict:
    events = ["kill", "objective", "round_end", "pause", "resume"]
    return {
        "type": "event",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "seq": seq,
        "event": random.choice(events),
        "meta": {"note": f"auto-generated event {seq}"},
    }


def run_seeder(match_id: str, interval: float = 2.0, count: int = 20) -> None:
    """Push `count` updates into the store for `match_id` every `interval` seconds."""
    for i in range(1, count + 1):
        # Alternate between score and event updates
        if i % 3 == 0:
            update = _make_event_update(i)
        else:
            update = _make_score_update(i)
        payload = {"match_id": match_id, "update": update}
        store.push_update(str(match_id), payload)
        print(f"Pushed update #{i} for match {match_id}: {json.dumps(update)}")
        time.sleep(interval)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--match-id", default="m1")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--count", type=int, default=20)
    args = p.parse_args()
    run_seeder(args.match_id, args.interval, args.count)
