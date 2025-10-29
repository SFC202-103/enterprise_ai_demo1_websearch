"""APScheduler-backed tracker worker with optional Redis-based distributed lock.

This module provides a single BackgroundScheduler instance and a job that
emits demo events for the persisted tracked selection. When `REDIS_URL` is
set the worker tries to acquire a short-lived lock using SET NX so only one
instance runs the job at a time in multi-instance deployments.

To enable the scheduler on app startup set env ENABLE_TRACKER=1 (or provide
REDIS_URL in the environment). This avoids starting background threads during
unit tests.
"""
from __future__ import annotations

import os
import time
import random
import asyncio
from typing import Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except Exception:  # pragma: no cover - optional in test env
    BackgroundScheduler = None  # type: ignore

try:
    import redis
except Exception:  # pragma: no cover - optional
    redis = None  # type: ignore

from src.backend_store import store

_lock_key = "esports:tracker:lock"
_lock_ttl = 10  # seconds
_scheduler: Optional[BackgroundScheduler] = None
_job = None


def _acquire_lock(r: "redis.Redis", key: str, ttl: int) -> bool:
    """Try to acquire a simple Redis lock using SET NX with expiry."""
    if r is None:
        return True
    try:
        # Use set with NX and PX
        return r.set(key, str(os.getpid()), nx=True, ex=ttl)
    except Exception:
        return False


def _release_lock(r: "redis.Redis", key: str) -> None:
    try:
        if r is not None:
            r.delete(key)
    except Exception:
        pass


def _run_job(loop_interval: float = 3.0):
    """Return the function to be scheduled by APScheduler.

    The returned function will be invoked in a thread by APScheduler; it
    performs lock acquisition (if Redis available), then emits events until
    the function returns. We keep each invocation short and stateless so the
    scheduler simply calls it repeatedly.
    """

    def job_func():
        r = None
        redis_url = os.getenv("REDIS_URL")
        if redis and redis_url:
            try:
                r = redis.from_url(redis_url)
            except Exception:
                r = None

        have_lock = True
        if r is not None:
            have_lock = _acquire_lock(r, _lock_key, _lock_ttl)

        if not have_lock:
            # Not the leader; skip this run.
            return

        try:
            # Read the tracked selection from DB if available, otherwise use
            # in-memory fallback provided by fastapi_app's _tracked (via API).
            try:
                from src import db as _db

                sel = _db.get_tracked_selection()
                match_id = sel.get("match_id") if sel else None
            except Exception:
                # Try reading from the in-memory store / fastapi_app helper
                try:
                    from src import fastapi_app as _fa

                    t = _fa.get_tracked()
                    # get_tracked may be async; handle both
                    if asyncio.iscoroutine(t):
                        # run it quickly
                        match = asyncio.get_event_loop().run_until_complete(t)
                    else:
                        match = t
                    match_id = match.get("match_id") if match else None
                except Exception:
                    match_id = None

            # If no tracked match, nothing to emit
            if not match_id:
                return

            # Emit a few realistic events per run
            # round / score state stored in-memory per match to keep things
            # light; store a tiny per-match state in store._updates keyed key
            state_key = f"__state__:{match_id}"
            current_state = getattr(store, "_meta", {}).get(state_key) if hasattr(store, "_meta") else None
            if current_state is None:
                current_state = {"home": 0, "away": 0, "round": 0}
                if not hasattr(store, "_meta"):
                    store._meta = {}
                store._meta[state_key] = current_state

            home = current_state["home"]
            away = current_state["away"]
            round_no = current_state["round"]

            # sometimes start a new round
            if random.random() < 0.3:
                round_no += 1
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "round_start", "round": round_no, "timestamp": time.time()}})

            # kills
            if random.random() < 0.7:
                killer = f"Player{random.randint(1,10)}"
                victim = f"Player{random.randint(11,20)}"
                which = "home" if random.random() < 0.5 else "away"
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "kill", "killer": killer, "victim": victim, "team": which, "timestamp": time.time()}})

            # objectives
            if random.random() < 0.2:
                obj = random.choice(["bomb_planted", "tower_destroyed", "flag_captured"])
                team = "home" if random.random() < 0.5 else "away"
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "objective", "objective": obj, "team": team, "timestamp": time.time()}})

            # round end
            if random.random() < 0.15:
                if random.random() < 0.55:
                    home += 1
                else:
                    away += 1
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "round_end", "round": round_no, "home": home, "away": away, "timestamp": time.time()}})
                # emit aggregate score
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "score", "home": home, "away": away, "timestamp": time.time()}})

            # heartbeat
            if random.random() < 0.25:
                store.push_update(str(match_id), {"match_id": str(match_id), "update": {"type": "score", "home": home, "away": away, "timestamp": time.time()}})

            # persist state
            current_state["home"] = home
            current_state["away"] = away
            current_state["round"] = round_no
            # Also persist to DB if available so leadership handoffs survive
            try:
                from src import db as _db

                try:
                    # store a timestamp and pid similar to tracker_tasks
                    _db.set_tracked_state(match_id, home, away, round_no, str(time.time()), str(os.getpid()))
                except Exception:
                    # best-effort persistence; don't fail the job if DB write fails
                    pass
            except Exception:
                # db not available in this runtime
                pass

        finally:
            if r is not None:
                try:
                    _release_lock(r, _lock_key)
                except Exception:
                    pass

    return job_func


def start_scheduler(interval: float = 3.0):
    global _scheduler, _job  # pylint: disable=global-statement
    if BackgroundScheduler is None:
        return
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler()
    _job = _scheduler.add_job(_run_job(interval), trigger=IntervalTrigger(seconds=interval))
    _scheduler.start()


def stop_scheduler():
    global _scheduler  # pylint: disable=global-statement
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        pass
    _scheduler = None
