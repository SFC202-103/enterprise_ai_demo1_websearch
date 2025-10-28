import time

from src.connectors import cache


def test_get_cached_and_clear():
    cache.clear_cache()

    def loader():
        return {"v": 1}

    v1 = cache.get_cached("k1", ttl=1.0, loader=loader)
    assert v1 == {"v": 1}

    # Immediately fetching again should return cached value (same object)
    v2 = cache.get_cached("k1", ttl=1.0, loader=lambda: {"v": 2})
    assert v2 == {"v": 1}

    # After TTL expires, loader should be called again
    time.sleep(1.1)
    v3 = cache.get_cached("k1", ttl=1.0, loader=lambda: {"v": 3})
    assert v3 == {"v": 3}

    info = cache.cache_info()
    assert isinstance(info, dict)

    cache.clear_cache()
    assert cache.cache_info() == {}
