def test_backend_store_push_get():
    from src.backend_store import InMemoryStore

    s = InMemoryStore()
    s.push_update("m1", {"score": 1})
    assert s.get_update("m1") == {"score": 1}
    # second get should return None
    assert s.get_update("m1") is None


def test_fastapi_app_loads():
    # Import the FastAPI module to ensure it loads and exposes `app`
    import importlib

    mod = importlib.import_module("src.fastapi_app")
    assert hasattr(mod, "app")
    # verify a couple of endpoints are present as callables
    assert callable(getattr(mod, "get_games", None))
    assert callable(getattr(mod, "get_matches", None))
