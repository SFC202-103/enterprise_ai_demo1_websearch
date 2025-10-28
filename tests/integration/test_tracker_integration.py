import os
import time
import pytest

pytestmark = pytest.mark.integration


def test_emit_events_with_redis_and_db(tmp_path):
    """Integration test that requires a Redis service and exercises
    src.tracker_tasks.emit_events. This test runs only when RUN_INTEGRATION=1
    and expects REDIS_URL to point to a reachable Redis instance.
    """
    # Require explicit opt-in to run integration tests to avoid flakiness
    if not os.getenv("RUN_INTEGRATION"):
        pytest.skip("Integration tests disabled; set RUN_INTEGRATION=1 to enable")

    # Preconditions
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        pytest.skip("REDIS_URL not set; skipping integration test")

    try:
        import redis as _redis
    except Exception:
        pytest.skip("redis package not available; skipping integration test")

    # Quick connectivity check
    try:
        r = _redis.from_url(redis_url)
        r.ping()
    except Exception:
        pytest.skip("Cannot connect to Redis at REDIS_URL; skipping")

    # Prepare an ephemeral sqlite DB for this test
    db_file = tmp_path / "integration_db.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    # Import db helpers and initialize schema
    from src import db as _db

    _db.init_db()

    # Set a tracked selection so emit_events has something to operate on
    test_mid = "m_integration_1"
    _db.set_tracked_selection(test_mid, "Team A")

    # Ensure the backend store is empty
    from src.backend_store import store

    # Call emit_events once — it should acquire redis lock and push one or more updates
    from src.tracker_tasks import emit_events

    # Run the emitter
    emit_events(loop_interval=0.01)

    # Give a short time for any background operations (if any)
    time.sleep(0.1)

    # Collect at least one update from the store
    updates = []
    while True:
        u = store.get_update(test_mid)
        if u is None:
            break
        updates.append(u)

    assert len(updates) > 0, "emit_events did not push any updates into the store"

    # --- Now exercise the APScheduler-backed worker if available ---
    try:
        from src import tracker_worker as _tw
    except Exception:
        pytest.skip("tracker_worker not importable; skipping scheduler portion")

    # If APScheduler isn't installed in the environment, skip this portion.
    if getattr(_tw, "BackgroundScheduler", None) is None:
        pytest.skip("APScheduler not available; skipping scheduler portion")

    # start the scheduler with a short interval, let it run once, then stop
    _tw.start_scheduler(interval=1.0)
    try:
        # allow one scheduled run to execute
        time.sleep(1.2)
    finally:
        _tw.stop_scheduler()

    # Collect any further updates produced by the scheduler run
    more = []
    while True:
        u = store.get_update(test_mid)
        if u is None:
            break
        more.append(u)

    assert len(more) > 0, "Scheduler did not push any updates into the store"

    # Verify the scheduler persisted tracked state to the DB
    try:
        state = _db.get_tracked_state(test_mid)
    except Exception:
        state = None

    assert state is not None, "Tracked state was not persisted to the DB by the scheduler"
    # Expect the persisted state to include numeric home/away or at least a timestamp/pid
    assert isinstance(state.get("home"), int) and isinstance(state.get("away"), int)