"""Simple in-memory store for demo live updates."""
from typing import Any, Dict, List, Optional


class InMemoryStore:
    """Very small FIFO store for per-match updates used by the demo WebSocket.

    This is intentionally tiny and not intended for production. It lets the
    FastAPI websocket handler pull queued updates for a match ID.
    """

    def __init__(self) -> None:
        self._updates: Dict[str, List[Any]] = {}

    def push_update(self, match_id: str, update: Any) -> None:
        self._updates.setdefault(str(match_id), []).append(update)

    def get_update(self, match_id: str) -> Optional[Any]:
        lst = self._updates.get(str(match_id), [])
        if not lst:
            return None
        return lst.pop(0)


# Single global store instance used by the demo app
store = InMemoryStore()
