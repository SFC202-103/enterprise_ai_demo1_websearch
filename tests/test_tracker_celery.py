import importlib


def test_make_celery_returns_none_when_no_broker(monkeypatch):
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    mod = importlib.reload(__import__("src.celery_app", fromlist=["*"]))
    assert mod.make_celery() is None


def test_emit_events_no_db_no_redis(monkeypatch):
    # Ensure environment has no REDIS and no DB helpers
    monkeypatch.delenv("REDIS_URL", raising=False)
    # reload tracker_tasks and call emit_events; should not raise
    mod = importlib.reload(__import__("src.tracker_tasks", fromlist=["*"]))
    # call directly; with no DB/redis it will simply return
    mod.emit_events(loop_interval=0.01)


def test_celery_registration_with_fake_celery(monkeypatch):
    import sys
    import types
    # importlib is already imported at module level

    # fake celery module
    fake = types.ModuleType("celery")

    class FakeCelery:
        def __init__(self, name, broker=None):
            self.name = name
            self.broker = broker
            self.conf = types.SimpleNamespace(beat_schedule={}, timezone=None)

            class Tasks:
                def register(self, func):
                    setattr(self, func.__name__, func)

            self.tasks = Tasks()

    fake.Celery = FakeCelery
    monkeypatch.setitem(sys.modules, "celery", fake)

    # ensure broker env
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

    # reload celery_app and tracker_tasks to trigger registration
    ca = importlib.reload(__import__("src.celery_app", fromlist=["*"]))
    _ = importlib.reload(__import__("src.tracker_tasks", fromlist=["*"]))

    # make_celery should now return a FakeCelery
    celery = ca.make_celery()
    assert celery is not None
    # the tracker_tasks module should have attempted to register the task
    # via celery; check beat schedule contains our task key (if set)
    assert isinstance(celery.conf.beat_schedule, dict)


def test_emit_events_with_fake_db_and_redis(monkeypatch):
    import sys
    import types
    # importlib is already imported at module level

    # fake redis client
    fake_redis_mod = types.ModuleType("redis")

    class FakeClient:
        def __init__(self):
            self._store = {}

        def set(self, key, val, nx=False, ex=None):
            if nx and key in self._store:
                return False
            self._store[key] = val
            return True

        def delete(self, key):
            self._store.pop(key, None)

    def from_url(url):
        return FakeClient()

    fake_redis_mod.from_url = from_url
    monkeypatch.setitem(sys.modules, "redis", fake_redis_mod)

    # fake db module
    fake_db = types.ModuleType("src.db")

    _saved = {}

    def get_tracked_selection():
        return {"match_id": "m1", "team": "Home"}

    def get_tracked_state(match_id):
        return {}

    def set_tracked_state(match_id, home, away, round_no, last_run, leader_pid):
        _saved["match_id"] = match_id
        _saved["home"] = home
        _saved["away"] = away
        _saved["round"] = round_no
        _saved["last_run"] = last_run
        _saved["leader_pid"] = leader_pid
        return _saved

    fake_db.get_tracked_selection = get_tracked_selection
    fake_db.get_tracked_state = get_tracked_state
    fake_db.set_tracked_state = set_tracked_state

    monkeypatch.setitem(sys.modules, "src.db", fake_db)
    # ensure the src package references our fake db (in case src was already imported)
    import src as _src_pkg
    setattr(_src_pkg, "db", fake_db)

    # reload tracker_tasks so it picks up fake db/redis
    tt = importlib.reload(__import__("src.tracker_tasks", fromlist=["*"]))
    # clear any store state
    from src.backend_store import store
    store._updates.clear()

    # make random deterministic so the emitter will produce at least one event
    import random as _random
    monkeypatch.setattr(_random, "random", lambda: 0.01)
    monkeypatch.setattr(_random, "randint", lambda a, b: a)
    monkeypatch.setattr(_random, "choice", lambda seq: seq[0])

    # call the emit function
    tt.emit_events(loop_interval=0.01)

    # ensure that state was saved to fake db
    assert _saved.get("match_id") == "m1"
    # ensure store saw some updates for m1
    assert "m1" in store._updates


def test_emit_events_for_all_branches(monkeypatch):
    """Force random branches to execute and ensure persistence and store pushes."""
    import sys
    import types
    import os
    # importlib is already imported at module level

    # fake db
    fake_db = types.ModuleType("src.db")

    saved = {}

    def get_tracked_selection():
        return {"match_id": "m-all", "team": "Home"}

    def get_tracked_state(match_id):
        return {"home": 0, "away": 0, "round": 0}

    def set_tracked_state(match_id, home, away, round_no, last_run, leader_pid):
        saved["match_id"] = match_id
        saved["home"] = home
        saved["away"] = away
        saved["round"] = round_no

    fake_db.get_tracked_selection = get_tracked_selection
    fake_db.get_tracked_state = get_tracked_state
    fake_db.set_tracked_state = set_tracked_state

    monkeypatch.setitem(sys.modules, "src.db", fake_db)
    import src as _src_pkg
    setattr(_src_pkg, "db", fake_db)

    # fake redis
    fake_redis = types.ModuleType("redis")

    class FakeClient:
        def set(self, key, val, nx=False, ex=None):
            return True

        def delete(self, key):
            return None

    def from_url(url):
        return FakeClient()

    fake_redis.from_url = from_url
    monkeypatch.setitem(sys.modules, "redis", fake_redis)

    # ensure REDIS_URL is set so tracker_tasks will try to use redis
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    # force random to always trigger branches
    monkeypatch.setattr("random.random", lambda: 0.01)
    monkeypatch.setattr("random.randint", lambda a, b: a)
    monkeypatch.setattr("random.choice", lambda lst: lst[0])

    # reload module and run
    tt = importlib.reload(__import__("src.tracker_tasks", fromlist=["*"]))
    from src.backend_store import store
    store._updates.clear()

    tt.emit_events()

    assert saved.get("match_id") == "m-all"
    assert "m-all" in store._updates


def test_reload_import_time_variants(monkeypatch):
    """Reload src.tracker_tasks under different import failure scenarios to
    exercise the module-level try/except import paths.
    """
    import builtins
    import sys
    import types
    # importlib is already imported at module level

    # First variant: force ImportError for redis and celery app
    real_import = builtins.__import__

    def failing_import(name, glob=None, loc=None, fromlist=(), level=0):
        if name in ("redis", "src.celery_app"):
            raise ImportError("simulated missing")
        return real_import(name, glob, loc, fromlist, level)

    builtins.__import__ = failing_import
    try:
        import src.tracker_tasks as tt
        importlib.reload(tt)
    finally:
        builtins.__import__ = real_import

    # Second variant: provide a fake celery_app so registration branch runs
    fake_celery_mod = types.ModuleType("src.celery_app")

    class FakeCelery:
        def __init__(self):
            self.tasks = types.SimpleNamespace()
            # simple dict-like conf with beat_schedule attribute
            self.conf = types.SimpleNamespace(beat_schedule={})

        def tasks_register(self, fn):
            pass

    def make_celery():
        return FakeCelery()

    fake_celery_mod.make_celery = make_celery
    monkeypatch.setitem(sys.modules, "src.celery_app", fake_celery_mod)

    # reload now; this should hit the celery registration path
    importlib.reload(__import__("src.tracker_tasks", fromlist=["*"]))
