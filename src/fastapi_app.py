"""Minimal FastAPI prototype serving esports-like data from fixtures.

This module provides a few simple endpoints that read the existing
`tests/fixtures/sample_responses.json` fixture and a tiny websocket that
polls the in-memory store for demo live updates.

Run with: `uvicorn src.fastapi_app:app --reload` (after installing FastAPI & uvicorn)
"""
from pathlib import Path
import json
import asyncio
import os
from typing import Any, Dict, List, Optional

from src.backend_store import store


# FastAPI is optional for tests. Import lazily and fall back to stubs so the
# module can be imported even when FastAPI isn't installed in the environment.
try:
    from fastapi import FastAPI, WebSocket  # type: ignore
    from fastapi.responses import JSONResponse  # type: ignore
    FASTAPI_AVAILABLE = True
except Exception:
    FASTAPI_AVAILABLE = False


_fixture_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_responses.json"
_fixture_data: Dict[str, Any] = {}
if _fixture_path.exists():
    try:
        with open(_fixture_path, "r", encoding="utf-8") as fh:
            _fixture_data = json.load(fh)
    except Exception:
        _fixture_data = {}


async def get_games() -> Dict[str, List[str]]:
    return {"games": ["overwatch", "valorant", "league_of_legends"]}


async def get_tournaments(game: str = None) -> Any:
    if not _fixture_data:
        return []
    return _fixture_data.get("tournaments", [])


async def get_matches() -> Any:
    # If a PandaScore token is set, prefer fetching live matches from that
    # connector. This keeps the fixture as a fallback for environments where
    # no API key is configured (e.g., tests).
    try:
        import os
        token = os.getenv("PANDASCORE_TOKEN")
        if token:
            from src.connectors.pandascore_connector import PandaScoreConnector

            try:
                conn = PandaScoreConnector(token)
                # Use 'video_game' value mapping if needed; for now allow None
                matches = conn.get_matches()
                return matches
            except Exception:
                # If the connector fails, fall back to the fixture
                pass
    except Exception:
        # Import or environment errors — fall back to fixture
        pass

    if not _fixture_data:
        return []
    return _fixture_data.get("matches", [])


async def get_match(match_id: str) -> Any:
    if not _fixture_data:
        if FASTAPI_AVAILABLE:
            return JSONResponse(status_code=404, content={"detail": "not found"})
        return {"detail": "not found"}
    matches = _fixture_data.get("matches", [])
    for m in matches:
        if str(m.get("id")) == str(match_id):
            return m
    if FASTAPI_AVAILABLE:
        return JSONResponse(status_code=404, content={"detail": "not found"})
    return {"detail": "not found"}


async def websocket_match_updates(websocket: "WebSocket", match_id: str):
    """Poll queued demo updates and push them to the websocket client.

    This function is only registered as a websocket handler when FastAPI is
    available. When FastAPI is missing the function still exists so imports
    succeed but it isn't used.
    """
    await websocket.accept()
    try:
        while True:
            update = store.get_update(match_id)
            if update is not None:
                await websocket.send_json(update)
            await asyncio.sleep(1.0)
    except Exception:
        await websocket.close()


async def push_update(payload: dict) -> dict:
    """Admin helper to push a demo update into the in-memory store.

    Expected payload: {"match_id": "m1", "update": {...}}
    This endpoint is registered only when FastAPI is available so it can be
    called (e.g., with curl or a simple admin UI) to seed live updates.
    """
    match_id = payload.get("match_id")
    update = payload.get("update")
    if not match_id or update is None:
        return {"ok": False, "error": "match_id and update required"}
    store.push_update(str(match_id), update)
    return {"ok": True}


def _is_admin(token: Optional[str]) -> bool:
    """Return True if the provided token matches the ADMIN_API_KEY env var.

    If ADMIN_API_KEY is not set, return False (require an explicit key).
    """
    if not token:
        return False
    expected = os.getenv("ADMIN_API_KEY")
    if not expected:
        return False
    return token == expected


async def admin_sync_impl(payload: dict, admin_token: Optional[str]) -> dict:
    if not _is_admin(admin_token):
        return {"ok": False, "error": "admin token missing or invalid"}

    connector_name = (payload or {}).get("connector")
    game = (payload or {}).get("game")
    if not connector_name:
        return {"ok": False, "error": "connector required"}

    connector_name = connector_name.lower()
    matches = []
    try:
        if connector_name == "pandascore":
            from src.connectors.pandascore_connector import PandaScoreConnector

            conn = PandaScoreConnector()
            matches = conn.get_matches(game=game)
        elif connector_name == "riot":
            from src.connectors.riot_connector import RiotConnector

            conn = RiotConnector()
            matches = conn.get_matches(game=game)
        else:
            return {"ok": False, "error": f"unknown connector: {connector_name}"}
    except ValueError as ve:
        return {"ok": False, "error": str(ve)}
    except Exception as exc:  # pragma: no cover - bubble up connector issues
        return {"ok": False, "error": f"connector error: {exc!s}"}

    pushed = 0
    for m in matches:
        mid = m.get("id") or m.get("match_id") or "unknown"
        store.push_update(str(mid), {"type": "sync", "match": m})
        pushed += 1

    return {"ok": True, "pushed": pushed}


async def admin_sync(payload: dict) -> dict:
    """Admin endpoint to fetch matches from a named connector and push them
    into the in-memory demo store.

    Expected payload: {"connector": "pandascore"|"riot", "game": "valorant"}
    This is intentionally permissive for the prototype; in production protect
    this endpoint behind auth and rate limits.
    """
    connector_name = (payload or {}).get("connector")
    game = (payload or {}).get("game")
    if not connector_name:
        return {"ok": False, "error": "connector required"}

    connector_name = connector_name.lower()
    matches = []
    try:
        if connector_name == "pandascore":
            from src.connectors.pandascore_connector import PandaScoreConnector

            conn = PandaScoreConnector()
            matches = conn.get_matches(game=game)
        elif connector_name == "riot":
            from src.connectors.riot_connector import RiotConnector

            conn = RiotConnector()
            matches = conn.get_matches(game=game)
        else:
            return {"ok": False, "error": f"unknown connector: {connector_name}"}
    except ValueError as ve:
        return {"ok": False, "error": str(ve)}
    except Exception as exc:  # pragma: no cover - bubble up connector issues
        return {"ok": False, "error": f"connector error: {exc!s}"}

    pushed = 0
    for m in matches:
        mid = m.get("id") or m.get("match_id") or "unknown"
        store.push_update(str(mid), {"type": "sync", "match": m})
        pushed += 1

    return {"ok": True, "pushed": pushed}


# Create and register endpoints only when FastAPI is present to avoid
# import-time failures in environments without the package.
if FASTAPI_AVAILABLE:
    app = FastAPI(title="Esports Demo API")
    # Add a permissive CORS policy for local development. In production,
    # restrict origins to your deployed frontend domains.
    try:
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception:
        # If CORSMiddleware import fails for some reason, continue without it.
        pass
    app.get("/api/games")(get_games)
    app.get("/api/tournaments")(get_tournaments)
    app.get("/api/matches")(get_matches)
    app.get("/api/matches/{match_id}")(get_match)
    # Admin endpoint to push demo updates (POST JSON {match_id, update})
    # Wrap the impls with header-based admin token extraction so the same
    # functions can be called directly in tests without FastAPI.
    try:
        from fastapi import Header  # type: ignore

        async def push_update_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
            if not _is_admin(x_admin_token):
                return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
            return await push_update(payload)

        async def admin_sync_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
            if not _is_admin(x_admin_token):
                return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
            return await admin_sync_impl(payload, x_admin_token)

        app.post("/api/admin/push_update")(push_update_endpoint)
        app.post("/api/admin/sync_matches")(admin_sync_endpoint)
    except Exception:
        # If Header import or wrapper creation fails, fall back to direct
        # registration of the underlying functions.
        app.post("/api/admin/push_update")(push_update)
        app.post("/api/admin/sync_matches")(admin_sync)
    app.websocket("/ws/matches/{match_id}")(websocket_match_updates)
else:
    # Provide a placeholder `app` so tests that assert its existence pass.
    app = None
