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


async def list_db_tournaments() -> Any:
    """Return tournaments from the DB if present, otherwise an empty list.

    This endpoint is useful once `src.db` has additional models and data.
    """
    try:
        from src import db as _db
        with _db.SessionLocal() as session:
            rows = session.query(_db.Tournament).all()
            return [r.to_dict() for r in rows]
    except Exception:
        return []


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


async def sse_match_updates(match_id: str):
    """Server-Sent Events (SSE) endpoint generator for match updates.

    Clients can connect with EventSource to receive JSON updates.
    This generator polls the `store` for queued updates and yields them
    as SSE `data:` frames.
    """
    # Use an async loop to poll for updates and yield SSE frames
    try:
        while True:
            update = store.get_update(match_id)
            if update is not None:
                # SSE requires lines starting with 'data: '
                payload = json.dumps(update)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        return
    except Exception:
        return


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


# Track a random team/match on startup for demo purposes. We store a small
# dict in-memory with the tracked match id and team name and provide a
# lightweight endpoint so the frontend can discover what is being tracked.
_tracked: dict = {"match_id": None, "team": None}


def _start_random_tracker(loop_interval: float = 3.0):
    """Start a background thread that pushes periodic random score updates
    for a randomly selected match from the fixture data. This keeps the
    demo UI lively without requiring manual seeding.
    """
    import random
    async def _bg():
        # choose an initial match from fixtures if available
        matches = _fixture_data.get("matches", []) if _fixture_data else []
        mid = None
        home = 0
        away = 0
        round_no = 0
        # helper to emit a score update
        def emit_score(m):
            payload = {"type": "score", "home": home, "away": away, "timestamp": __import__('time').time()}
            store.push_update(str(m), {"match_id": str(m), "update": payload})

        try:
            while True:
                # re-read tracked selection from DB if available so admin changes take effect
                try:
                    from src import db as _db

                    sel = _db.get_tracked_selection()
                    if sel and sel.get("match_id"):
                        if mid != str(sel.get("match_id")):
                            # switching tracked match resets counters
                            mid = str(sel.get("match_id"))
                            home = 0
                            away = 0
                            round_no = 0
                        tracked_team = sel.get("team")
                    else:
                        tracked_team = None
                except Exception:
                    # no DB available — fall back to fixture-driven pick
                    tracked_team = None
                    if mid is None and matches:
                        m = random.choice(matches)
                        mid = m.get("id") or m.get("match_id") or f"m_random_{random.randint(100,999)}"

                if mid is None:
                    await asyncio.sleep(loop_interval)
                    continue

                # Start a new round occasionally
                if random.random() < 0.3:
                    round_no += 1
                    payload = {"type": "round_start", "round": round_no, "timestamp": __import__('time').time()}
                    store.push_update(str(mid), {"match_id": str(mid), "update": payload})

                # Emit a few events per tick: kills/objectives with realistic weights
                # Kills
                if random.random() < 0.7:
                    killer = f"Player{random.randint(1,10)}"
                    victim = f"Player{random.randint(11,20)}"
                    which = "home" if random.random() < 0.5 else "away"
                    payload = {"type": "kill", "killer": killer, "victim": victim, "team": which, "timestamp": __import__('time').time()}
                    store.push_update(str(mid), {"match_id": str(mid), "update": payload})

                # Objective events (e.g., bomb planted, tower destroyed)
                if random.random() < 0.2:
                    obj = random.choice(["bomb_planted", "tower_destroyed", "flag_captured"])
                    team = "home" if random.random() < 0.5 else "away"
                    payload = {"type": "objective", "objective": obj, "team": team, "timestamp": __import__('time').time()}
                    store.push_update(str(mid), {"match_id": str(mid), "update": payload})

                # Round end and score increments
                if random.random() < 0.15:
                    # award the round to one side
                    if random.random() < 0.55:
                        home += 1
                    else:
                        away += 1
                    payload = {"type": "round_end", "round": round_no, "home": home, "away": away, "timestamp": __import__('time').time()}
                    store.push_update(str(mid), {"match_id": str(mid), "update": payload})
                    # also emit aggregate score
                    emit_score(mid)

                # Occasionally emit a heartbeat score so frontend can update
                if random.random() < 0.25:
                    emit_score(mid)

                await asyncio.sleep(loop_interval)
        except asyncio.CancelledError:
            return

    # schedule the background task
    try:
        asyncio.create_task(_bg())
    except Exception:
        # If event loop isn't running yet (e.g., tests), just ignore.
        pass


async def get_tracked() -> dict:
    """Return the currently tracked match/team for demo purposes."""
    # Prefer DB-backed tracked selection when available
    try:
        from src import db as _db

        row = _db.get_tracked_selection()
        if row:
            return {"match_id": row.get("match_id"), "team": row.get("team")}
    except Exception:
        pass
    return _tracked


async def set_tracked_impl(payload: dict, admin_token: Optional[str]) -> dict:
    """Protected setter for the tracked match/team.

    Expected payload: {"match_id": "m1", "team": "Team Name"}
    This function performs admin token validation when called via the
    FastAPI header wrapper. A non-authenticated setter `set_tracked`
    is provided for the test/import fallback registration.
    """
    if not _is_admin(admin_token):
        return {"ok": False, "error": "admin token missing or invalid"}
    match_id = payload.get("match_id") if payload else None
    team = payload.get("team") if payload else None
    try:
        from src import db as _db

        tracked = _db.set_tracked_selection(match_id, team)
        return {"ok": True, "tracked": tracked}
    except Exception:
        # Fall back to in-memory behavior
        if match_id:
            _tracked["match_id"] = str(match_id)
        if team is not None:
            _tracked["team"] = team
        return {"ok": True, "tracked": _tracked}


async def set_tracked(payload: dict) -> dict:
    """Non-authenticated setter used as a fallback when FastAPI Header
    wrappers are not available (e.g., in tests that mock fastapi)."""
    match_id = payload.get("match_id") if payload else None
    team = payload.get("team") if payload else None
    try:
        from src import db as _db

        tracked = _db.set_tracked_selection(match_id, team)
        return {"ok": True, "tracked": tracked}
    except Exception:
        if match_id:
            _tracked["match_id"] = str(match_id)
        if team is not None:
            _tracked["team"] = team
        return {"ok": True, "tracked": _tracked}


async def set_tracked(payload: dict, x_admin_token: Optional[str] = None) -> dict:
    """Admin endpoint to set the tracked match/team for the demo.

    Expected payload: {"match_id": "m1", "team": "Team Name"}
    Requires X-Admin-Token header to match ADMIN_API_KEY.
    """
    if not _is_admin(x_admin_token):
        return {"ok": False, "error": "admin token missing or invalid"}
    match_id = payload.get("match_id")
    team = payload.get("team")
    if not match_id:
        return {"ok": False, "error": "match_id required"}
    _tracked["match_id"] = str(match_id)
    _tracked["team"] = team or _tracked.get("team")
    # push a small sync notice into the store so clients refresh metadata
    store.push_update(str(match_id), {"type": "sync", "match_id": str(match_id), "team": _tracked.get("team")})
    return {"ok": True, "tracked": _tracked}


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
    app.get("/api/db/tournaments")(list_db_tournaments)
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
        async def set_tracked_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
            return await set_tracked_impl(payload, x_admin_token)

        app.post("/api/tracked")(set_tracked_endpoint)
    except Exception:
        # If Header import or wrapper creation fails, fall back to direct
        # registration of the underlying functions.
        app.post("/api/admin/push_update")(push_update)
        app.post("/api/admin/sync_matches")(admin_sync)
        # Expose non-auth tracked setter for test environments that don't
        # provide Header-aware wrappers.
        app.post("/api/tracked")(set_tracked)
    app.websocket("/ws/matches/{match_id}")(websocket_match_updates)
    # SSE endpoint for clients that prefer EventSource over WebSockets
    # StreamingResponse may not be available on mocked fastapi.responses used
    # by tests; import it defensively and fall back to a no-op generator
    try:
        from fastapi.responses import StreamingResponse as _StreamingResponse  # type: ignore
    except Exception:
        _StreamingResponse = None

    async def _sse_endpoint(match_id: str):
        if _StreamingResponse is not None:
            return _StreamingResponse(sse_match_updates(match_id), media_type="text/event-stream")
        # Fallback: return the generator directly. When FastAPI is real this
        # path won't be used; it's only to keep imports working in tests that
        # mock fastapi.responses.
        return sse_match_updates(match_id)

    app.get("/api/stream/matches/{match_id}")(_sse_endpoint)
    # Endpoint to let the frontend know which match/team is being auto-tracked
    app.get("/api/tracked")(get_tracked)
    # Admin-protected endpoint to set tracked match/team
    try:
        from fastapi import Header  # type: ignore

        async def set_tracked_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
            if not _is_admin(x_admin_token):
                return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
            return await set_tracked(payload, x_admin_token)

        app.post("/api/tracked")(set_tracked_endpoint)
    except Exception:
        # Fallback: register unprotected if Header isn't available (test-only)
        app.post("/api/tracked")(set_tracked)

    # Start the demo random tracker on application startup so the demo UI
    # receives live updates without manual seeding. Register the handler
    # defensively because unit tests may provide a minimal DummyApp that
    # doesn't implement `on_event`.
    def _register_startup():
        try:
            if hasattr(app, "on_event"):
                @app.on_event("startup")
                async def _on_startup():
                    try:
                        _start_random_tracker(loop_interval=3.0)
                    except Exception:
                        pass
            elif hasattr(app, "add_event_handler"):
                # older FastAPI/Starlette API
                try:
                    app.add_event_handler("startup", lambda: _start_random_tracker(loop_interval=3.0))
                except Exception:
                    pass
        except Exception:
            # If registration fails in test environments, ignore.
            pass

    _register_startup()
else:
    # Provide a placeholder `app` so tests that assert its existence pass.
    app = None
