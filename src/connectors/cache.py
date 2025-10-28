"""Very small in-memory TTL cache for connector responses.

This is intentionally tiny and process-local. It's useful for demo purposes
and reduces repeated calls to external APIs during short test loops.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple

_cache: Dict[str, Tuple[float, Any]] = {}


def get_cached(key: str, ttl: float, loader: Callable[[], Any]) -> Any:
    """Return cached value for key if fresh; otherwise call loader(), cache and return it.

    loader is a zero-arg callable that produces the value.
    """
    now = time.time()
    ent = _cache.get(key)
    if ent is not None:
        ts, val = ent
        if now - ts < ttl:
            return val
    val = loader()
    _cache[key] = (now, val)
    return val


def clear_cache() -> None:
    _cache.clear()


def cache_info() -> Dict[str, Any]:
    return {k: (time.time() - ts) for k, (ts, _) in _cache.items()}
