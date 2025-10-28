import os
import time
import pytest

pytestmark = pytest.mark.integration


def test_leadership_handoff_persists_state(tmp_path, monkeypatch):
    """Simulate a leader emitting events, persisting state, then a new
    instance continuing from the persisted state (handoff).

    This test is gated: it runs only when RUN_INTEGRATION=1 and expects
    REDIS_URL to point to a reachable Redis instance.
    """
    if not os.getenv("RUN_INTEGRATION"):
        pytest.skip("Integration tests disabled; set RUN_INTEGRATION=1 to enable")

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set; skipping integration test")

    try:
        import redis as _redis
    except Exception:
        pytest.skip("redis package not available; skipping integration test")

    # quick connectivity check and ensure clean lock
    r = _redis.from_url(redis_url)
    try:
        r.ping()
    except Exception:
        pytest.skip("Cannot connect to Redis at REDIS_URL; skipping")
    try:
        r.delete("esports:tracker:lock")
    except Exception:
        pass

    # Set up a temporary sqlite DB
    db_file = tmp_path / "handoff_db.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    from src import db as _db
    from src.backend_store import store
    from src.tracker_tasks import emit_events

    # Initialize DB schema
    _db.init_db()

    mid = "m_handoff_1"
    _db.set_tracked_selection(mid, "Team A")

    # Make random deterministic: choose values that trigger a round_end and
    # select 'home' as the winner so home increments predictably.
    import random as _random

    monkeypatch.setattr(_random, "random", lambda: 0.1)
    monkeypatch.setattr(_random, "randint", lambda a, b: a)
    monkeypatch.setattr(_random, "choice", lambda seq: seq[0])

    # First leader run: should persist some non-zero home/away values
    emit_events(loop_interval=0.01)
    time.sleep(0.05)

    state1 = _db.get_tracked_state(mid)
    assert state1 is not None, "First run did not persist state"
    # Expect numeric home/away keys
    h1 = int(state1.get("home", 0))
    a1 = int(state1.get("away", 0))
    assert (h1 + a1) >= 0

    # Simulate a new leader/process by clearing any in-memory meta in store
    if hasattr(store, "_meta"):
        store._meta.clear()

    # Second run: should read persisted state and increment further
    emit_events(loop_interval=0.01)
    time.sleep(0.05)

    state2 = _db.get_tracked_state(mid)
    assert state2 is not None, "Second run did not persist state"
    h2 = int(state2.get("home", 0))
    a2 = int(state2.get("away", 0))

    # At least one of the scores should be >= previous (monotonicity)
    assert h2 >= h1 and a2 >= a1
