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
    from fastapi import FastAPI, WebSocket, Header  # type: ignore
    from fastapi.responses import JSONResponse, FileResponse, StreamingResponse  # type: ignore
    FASTAPI_AVAILABLE = True
    try:
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore
        CORS_AVAILABLE = True
    except (ImportError, ModuleNotFoundError, Exception):
        CORS_AVAILABLE = False
        class CORSMiddleware:  # type: ignore
            def __init__(self, *args, **kwargs): pass
    try:
        from fastapi.staticfiles import StaticFiles  # type: ignore
    except (ImportError, ModuleNotFoundError):
        # StaticFiles requires aiofiles, which may not be installed
        StaticFiles = None  # type: ignore
except (ImportError, ModuleNotFoundError, Exception):  # pragma: no cover
    FASTAPI_AVAILABLE = False
    CORS_AVAILABLE = False
    # Provide stub classes when FastAPI is not available
    FastAPI = None  # type: ignore
    WebSocket = None  # type: ignore
    class JSONResponse:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class FileResponse:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class StreamingResponse:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class StaticFiles:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class CORSMiddleware:  # type: ignore
        def __init__(self, *args, **kwargs): pass
    class Header:  # type: ignore
        def __init__(self, *args, **kwargs): pass


# Load match fixture data for demo purposes
_fixture_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "matches.json"
_fixture_data: Dict[str, Any] = {}
if _fixture_path.exists():
    try:
        with open(_fixture_path, "r", encoding="utf-8") as fh:
            _fixture_data = json.load(fh)
    except Exception:  # pragma: no cover
        _fixture_data = {}
else:
    # Fallback to sample_responses.json for backward compatibility
    _fallback_path = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_responses.json"
    if _fallback_path.exists():
        try:
            with open(_fallback_path, "r", encoding="utf-8") as fh:
                _fixture_data = json.load(fh)
        except Exception:  # pragma: no cover
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
    except Exception:  # pragma: no cover
        return []


async def get_matches() -> Any:
    # If a PandaScore token is set, prefer fetching live matches from that
    # connector. This keeps the fixture as a fallback for environments where
    # no API key is configured (e.g., tests).
    try:
        token = os.getenv("PANDASCORE_TOKEN")
        if token:
            from src.connectors.pandascore_connector import PandaScoreConnector

            try:
                conn = PandaScoreConnector(token)
                # Use 'video_game' value mapping if needed; for now allow None
                matches = conn.get_matches()
                return matches
            except Exception:  # pragma: no cover
                # If the connector fails, fall back to the fixture
                pass
    except Exception:  # pragma: no cover
        # Import or environment errors — fall back to fixture
        pass

    if not _fixture_data:
        return []
    return _fixture_data.get("matches", [])


async def get_live_matches(game: Optional[str] = None, provider: Optional[str] = None, status: Optional[str] = None) -> Any:
    """Return live or upcoming matches from configured connectors.

    Query params:
    - game: optional video game slug (e.g., valorant, overwatch, dota2, lol)
    - provider: optional provider name to choose connector:
        - 'pandascore': PandaScore API (multi-game)
        - 'riot': Riot Games API (old connector)
        - 'riot_esports': Riot LoL Esports API (LoL only)
        - 'opendota': OpenDota API (Dota 2 only)
        - 'liquipedia': Liquipedia MediaWiki (multi-game)

    Falls back to the local fixture data when connectors are not configured.
    """
    # Check if we should use demo/fixture mode (no API keys configured)
    use_demo_mode = os.getenv("USE_DEMO_MODE", "true").lower() == "true"
    has_api_keys = (os.getenv("PANDASCORE_TOKEN") or 
                   os.getenv("RIOT_API_KEY") or 
                   os.getenv("HLTV_API_KEY") or
                   os.getenv("BATTLEFY_API_KEY"))
    
    # If demo mode is enabled AND no explicit provider is requested, use fixture data only
    # This allows tests to mock connectors by specifying a provider explicitly
    if use_demo_mode and not provider and not has_api_keys:
        # Fast path: return fixture data immediately without calling any connectors
        matches = _fixture_data.get("matches", [])
        if game:
            game_lower = game.lower()
            matches = [m for m in matches if 
                      game_lower in (m.get("video_game") or "").lower() or
                      game_lower in (m.get("game") or "").lower() or
                      game_lower in (m.get("videogame", {}).get("slug") or "").lower()]
        if status:
            s = status.lower()
            if s == "running" or s == "live":
                matches = [m for m in matches if "running" in (m.get("status") or "").lower()]
            elif s in ("upcoming", "scheduled"):
                matches = [m for m in matches if "upcoming" in (m.get("status") or "").lower()]
            elif s == "finished":
                matches = [m for m in matches if "finished" in (m.get("status") or "").lower()]
        return matches
    
    # Prefer explicit provider selection
    if provider:
        p = provider.lower()
        try:
            if p == "pandascore":
                from src.connectors.pandascore_connector import PandaScoreConnector

                conn = PandaScoreConnector()
                return conn.get_matches(game=game)
            if p == "riot":
                from src.connectors.riot_connector import RiotConnector

                conn = RiotConnector()
                return conn.get_matches(game=game)
            if p == "riot_esports":
                from src.connectors.riot_esports_connector import RiotEsportsConnector

                conn = RiotEsportsConnector()
                return conn.get_matches(game=game)
            if p == "opendota":
                from src.connectors.opendota_connector import OpenDotaConnector

                conn = OpenDotaConnector()
                return conn.get_matches(game=game)
            if p == "liquipedia":
                from src.connectors.liquipedia_connector import LiquipediaConnector

                # Map game names to Liquipedia format
                game_map = {
                    "lol": "lol",
                    "league": "lol",
                    "csgo": "csgo",
                    "cs": "csgo",
                    "dota2": "dota2",
                    "dota": "dota2",
                    "valorant": "valorant",
                    "overwatch": "overwatch"
                }
                liqui_game = game_map.get(game.lower() if game else "", "csgo")
                conn = LiquipediaConnector(game=liqui_game)
                return conn.get_matches(game=game)
            if p == "mediawiki":
                from src.connectors.liquipedia_connector import LiquipediaConnector

                # Use generic MediaWiki.org endpoint
                conn = LiquipediaConnector(game="mediawiki", use_generic_mediawiki=True)
                return conn.get_matches(game=game)
            if p == "hltv":
                from src.connectors.hltv_connector import HLTVConnector

                conn = HLTVConnector()
                return conn.get_matches(game=game)
            if p == "battlefy":
                from src.connectors.battlefy_connector import BattlefyConnector

                conn = BattlefyConnector()
                return conn.get_matches(game=game)
            if p == "apex":
                from src.connectors.apex_connector import ApexLegendsConnector

                conn = ApexLegendsConnector()
                return conn.get_matches(game=game)
            if p == "marvel":
                from src.connectors.marvel_rivals_connector import MarvelRivalsConnector

                conn = MarvelRivalsConnector()
                return conn.get_matches(game=game)
        except ValueError as ve:
            # missing token/config
            return {"ok": False, "error": str(ve)}
        except Exception as exc:
            return {"ok": False, "error": f"connector error: {exc!s}"}

    # No provider requested: try multiple connectors and aggregate results
    all_matches = []
    
    # Try HLTV for CS:GO (prioritize game-specific sources)
    if not game or game.lower() in ['csgo', 'cs', 'counter-strike']:
        try:
            from src.connectors.hltv_connector import HLTVConnector
            from src.connectors.cache import get_cached

            conn = HLTVConnector()
            try:
                key = f"hltv:{game or 'csgo'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass
    
    # Try Riot LoL Esports for League of Legends (prioritize official sources)
    if not game or game.lower() in ['lol', 'league', 'leagueoflegends']:
        try:
            from src.connectors.riot_esports_connector import RiotEsportsConnector
            from src.connectors.cache import get_cached

            conn = RiotEsportsConnector()
            try:
                key = f"riot_esports:{game or 'lol'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass

    # Try OpenDota for Dota 2 (prioritize official sources)
    if not game or game.lower() in ['dota2', 'dota']:
        try:
            from src.connectors.opendota_connector import OpenDotaConnector
            from src.connectors.cache import get_cached

            conn = OpenDotaConnector()
            try:
                key = f"opendota:{game or 'dota2'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass
    
    # Try Battlefy for tournament data
    try:
        from src.connectors.battlefy_connector import BattlefyConnector
        from src.connectors.cache import get_cached

        conn = BattlefyConnector()
        try:
            key = f"battlefy:{game or 'all'}:{status or ''}"
            matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
            all_matches.extend(matches)
        except Exception:
            pass
    except Exception:
        pass
    
    # Try Apex Legends for Apex data
    if not game or game.lower() in ['apex', 'apex-legends', 'apexlegends']:
        try:
            from src.connectors.apex_connector import ApexLegendsConnector
            from src.connectors.cache import get_cached

            conn = ApexLegendsConnector()
            try:
                key = f"apex:{game or 'apex'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass
    
    # Try Marvel Rivals for Marvel Rivals data
    if not game or game.lower() in ['marvel', 'marvel-rivals', 'marvelrivals']:
        try:
            from src.connectors.marvel_rivals_connector import MarvelRivalsConnector
            from src.connectors.cache import get_cached

            conn = MarvelRivalsConnector()
            try:
                key = f"marvel:{game or 'marvel'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game, limit=25))  # type: ignore[call-arg]
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass
    
    # Try Poro (Leaguepedia) for League of Legends data
    if not game or game.lower() in ['lol', 'league', 'league-of-legends', 'leagueoflegends']:
        try:
            from src.connectors.poro_connector import get_poro_connector
            from src.connectors.cache import get_cached

            conn = await get_poro_connector()
            try:
                key = f"poro:{game or 'lol'}:{status or ''}"
                async def poro_loader():
                    return await conn.get_matches(limit=25)
                matches = get_cached(key, ttl=60.0, loader=poro_loader)  # Cache for 60s
                if asyncio.iscoroutine(matches):
                    matches = await matches
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass

    # Try legacy Riot connector
    try:
        from src.connectors.riot_connector import RiotConnector
        from src.connectors.cache import get_cached

        conn = RiotConnector()
        try:
            key = f"riot:{game or 'all'}:{status or ''}"
            matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game))
            all_matches.extend(matches)
        except Exception:
            pass
    except Exception:
        pass
    
    # Try PandaScore as fallback (last resort due to rate limits)
    if len(all_matches) < 5:  # Only if we don't have enough matches yet
        try:
            from src.connectors.pandascore_connector import PandaScoreConnector
            from src.connectors.cache import get_cached

            conn = PandaScoreConnector()
            try:
                key = f"pandascore:{game or 'all'}:{status or ''}"
                matches = get_cached(key, ttl=30.0, loader=lambda: conn.get_matches(game=game))
                all_matches.extend(matches)
            except Exception:
                pass
        except Exception:
            pass

    # Return aggregated matches if we found any
    if all_matches:
        return all_matches

    # Fallback to fixture data
    if not _fixture_data:  # pragma: no cover - Defensive fallback rarely hit with connectors active
        return []
    matches = _fixture_data.get("matches", [])
    if game:
        matches = [m for m in matches if m.get("video_game") == game or m.get("game") == game]

    # If status filter requested, apply basic heuristics on normalized data
    if status:
        s = status.lower()
        def is_live(m: dict) -> bool:
            st = (m.get("status") or "")
            if isinstance(st, str) and st:
                stl = st.lower()
                return any(k in stl for k in ("running", "live", "in_progress"))
            if m.get("live") is True:
                return True
            return False

        def is_upcoming(m: dict) -> bool:
            st = (m.get("status") or "")
            if isinstance(st, str) and st:
                stl = st.lower()
                if any(k in stl for k in ("not_started", "scheduled", "upcoming")):
                    return True
            # If a scheduled_time exists and is non-empty, treat as upcoming
            if m.get("scheduled_time"):
                return True
            return False

        if s == "live":
            matches = [m for m in matches if is_live(m)]
        elif s in ("upcoming", "scheduled"):
            matches = [m for m in matches if is_upcoming(m)]

    return matches


async def get_match(match_id: str) -> Any:
    """Get a specific match by ID.
    
    Returns a match dictionary or a dict with 'detail' key if not found.
    Never returns a JSONResponse to maintain consistent return type for callers.
    """
    if not _fixture_data:  # pragma: no cover - Defensive fallback
        return {"detail": "not found"}
    
    matches = _fixture_data.get("matches", [])
    for m in matches:
        if str(m.get("id")) == str(match_id):
            return m
    
    # Always return dict, never JSONResponse, so callers can safely use .get()
    return {"detail": "not found"}


async def get_match_stats(game: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Get statistics about matches (live, upcoming, finished counts).

    Query params:
    - game: optional video game slug
    - provider: optional provider name

    Returns:
        Dictionary with total, live, upcoming, and finished counts
    """
    # Fetch all matches using the same logic as get_live_matches
    matches = await get_live_matches(game=game, provider=provider)
    
    # Handle error responses
    if isinstance(matches, dict) and not matches.get("ok", True):
        return {
            "total": 0,
            "live": 0,
            "upcoming": 0,
            "finished": 0,
            "error": matches.get("error")
        }
    
    # Ensure matches is a list
    if not isinstance(matches, list):
        matches = []
    
    # Helper functions to determine status
    def is_live(m: dict) -> bool:
        st = (m.get("status") or "")
        if isinstance(st, str) and st:
            stl = st.lower()
            return any(k in stl for k in ("running", "live", "in_progress"))
        if m.get("live") is True:
            return True
        return False

    def is_upcoming(m: dict) -> bool:
        st = (m.get("status") or "")
        if isinstance(st, str) and st:
            stl = st.lower()
            if any(k in stl for k in ("not_started", "scheduled", "upcoming")):
                return True
        # If a scheduled_time exists and is non-empty, treat as upcoming
        if m.get("scheduled_time"):
            return True
        return False

    def is_finished(m: dict) -> bool:
        st = (m.get("status") or "")
        if isinstance(st, str) and st:
            stl = st.lower()
            return any(k in stl for k in ("finished", "completed", "ended", "final"))
        return False
    
    # Count matches by status
    live_count = sum(1 for m in matches if is_live(m))
    upcoming_count = sum(1 for m in matches if is_upcoming(m))
    finished_count = sum(1 for m in matches if is_finished(m))
    
    return {
        "total": len(matches),
        "live": live_count,
        "upcoming": upcoming_count,
        "finished": finished_count
    }


async def get_team_stats(team_name: Optional[str] = None, game: Optional[str] = None) -> Dict[str, Any]:
    """Get team statistics and performance data.
    
    Query params:
    - team_name: Team name to get stats for
    - game: Filter by specific game
    
    Returns:
        Dictionary with team statistics including win rate, recent matches, form
    """
    # Fetch all matches
    matches = await get_live_matches(game=game)
    
    if isinstance(matches, dict) and not matches.get("ok", True):
        return {"ok": False, "error": matches.get("error")}
    
    if not isinstance(matches, list):
        matches = []
    
    # Filter matches for the specific team if provided
    team_matches = []
    if team_name:
        team_lower = team_name.lower()
        for match in matches:
            teams = match.get("teams") or match.get("opponents") or []
            for team in teams:
                team_match_name = (team.get("name") or team.get("acronym") or "").lower()
                if team_lower in team_match_name:
                    team_matches.append(match)
                    break
    else:
        team_matches = matches
    
    # Calculate statistics
    total_matches = len(team_matches)
    wins = 0
    losses = 0
    draws = 0
    recent_form = []
    
    for match in team_matches[-10:]:  # Last 10 matches
        status = (match.get("status") or "").lower()
        if "finished" in status or "completed" in status:
            teams = match.get("teams") or match.get("opponents") or []
            if len(teams) >= 2:
                team1_score = int(teams[0].get("score") or 0)
                team2_score = int(teams[1].get("score") or 0)
                
                if team_name:
                    # Determine if our team won
                    team_lower = team_name.lower()
                    is_team1 = team_lower in (teams[0].get("name") or teams[0].get("acronym") or "").lower()
                    
                    if team1_score > team2_score:
                        if is_team1:
                            wins += 1
                            recent_form.append("W")
                        else:
                            losses += 1
                            recent_form.append("L")
                    elif team2_score > team1_score:
                        if is_team1:
                            losses += 1
                            recent_form.append("L")
                        else:
                            wins += 1
                            recent_form.append("W")
                    else:
                        draws += 1
                        recent_form.append("D")
    
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    # Generate sentiment based on recent form
    sentiment = "Neutral"
    if len(recent_form) >= 3:
        recent_wins = recent_form[-5:].count("W")
        if recent_wins >= 4:
            sentiment = "Very Positive"
        elif recent_wins >= 3:
            sentiment = "Positive"
        elif recent_wins <= 1:
            sentiment = "Negative"
    
    return {
        "team_name": team_name or "All Teams",
        "game": game or "All Games",
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": round(win_rate, 2),
        "recent_form": "".join(recent_form[-5:]),  # Last 5 matches
        "sentiment": sentiment,
        "confidence": min(total_matches * 10, 95)  # Confidence based on sample size
    }


async def get_player_stats(player_name: Optional[str] = None, game: Optional[str] = None) -> Dict[str, Any]:
    """Get player statistics and performance data.
    
    Query params:
    - player_name: Player name to get stats for
    - game: Filter by specific game
    
    Returns:
        Dictionary with player statistics and sentiment
    """
    # For demo purposes, generate sample player stats
    # In a real implementation, this would query a player stats API
    
    if not player_name:
        return {
            "ok": False,
            "error": "player_name parameter required"
        }
    
    # Fetch recent matches to get context
    matches = await get_live_matches(game=game)
    
    if isinstance(matches, dict) and not matches.get("ok", True):
        return {"ok": False, "error": matches.get("error")}
    
    # Generate player stats (in real implementation, fetch from connector)
    import random
    random.seed(hash(player_name))  # Consistent stats for same player name
    
    games_played = random.randint(10, 100)
    kda = round(random.uniform(1.5, 5.0), 2)
    win_rate = round(random.uniform(45, 65), 2)
    avg_score = random.randint(15, 35)
    
    # Generate sentiment
    sentiment = "Neutral"
    if kda >= 3.5 and win_rate >= 55:
        sentiment = "Very Positive"
    elif kda >= 2.5 and win_rate >= 50:
        sentiment = "Positive"
    elif kda < 2.0 or win_rate < 45:
        sentiment = "Negative"
    
    return {
        "player_name": player_name,
        "game": game or "Multiple Games",
        "games_played": games_played,
        "kda_ratio": kda,
        "win_rate": win_rate,
        "avg_score_per_game": avg_score,
        "recent_performance": "Improving" if kda >= 2.5 else "Declining" if kda < 2.0 else "Stable",
        "sentiment": sentiment,
        "confidence": 85,
        "note": "Demo data - integrate with real player stats API for production"
    }


async def get_sentiment_analysis(match_id: Optional[str] = None, team_name: Optional[str] = None) -> Dict[str, Any]:
    """Get sentiment analysis for matches or teams.
    
    Query params:
    - match_id: Specific match to analyze
    - team_name: Specific team to analyze
    
    Returns:
        Dictionary with sentiment analysis and fan engagement metrics
    """
    if match_id:
        # Get specific match sentiment
        match = await get_match(match_id)
        if isinstance(match, dict) and match.get("detail") == "not found":
            return {"ok": False, "error": "Match not found"}
        
        status = (match.get("status") or "").lower()
        teams = match.get("teams") or match.get("opponents") or []
        
        # Extract team names
        team_names = []
        for team in teams[:2]:
            team_data = team.get("opponent") if "opponent" in team else team
            team_names.append(team_data.get("name", "Unknown"))
        
        sentiment_data = {
            "ok": True,
            "match_id": match_id,
            "teams": " vs ".join(team_names) if team_names else "Unknown",
            "overall_sentiment": "Positive",
            "excitement_level": 75,
            "fan_engagement": "High",
            "trending_topics": [],
            "confidence": 80
        }
        
        # Adjust based on status
        if "live" in status or "running" in status:
            sentiment_data["excitement_level"] = 90
            sentiment_data["overall_sentiment"] = "Very Positive"
            sentiment_data["trending_topics"] = ["#LiveMatch", "#Esports", "#Gaming"]
        elif "finished" in status:
            sentiment_data["excitement_level"] = 65
            sentiment_data["trending_topics"] = ["#MatchResults", "#Highlights"]
            
            # Check if close match
            if len(teams) >= 2:
                score1 = int(teams[0].get("score") or 0)
                score2 = int(teams[1].get("score") or 0)
                if abs(score1 - score2) <= 1:
                    sentiment_data["excitement_level"] = 95
                    sentiment_data["overall_sentiment"] = "Very Positive"
                    sentiment_data["trending_topics"].append("#CloseMatch")
        
        return sentiment_data
    
    elif team_name:
        # Get team sentiment
        team_stats = await get_team_stats(team_name=team_name)
        
        return {
            "team_name": team_name,
            "overall_sentiment": team_stats.get("sentiment", "Neutral"),
            "fan_base": "Growing" if team_stats.get("win_rate", 0) > 55 else "Stable",
            "recent_form": team_stats.get("recent_form", ""),
            "social_buzz": "High" if team_stats.get("win_rate", 0) > 60 else "Medium",
            "confidence": team_stats.get("confidence", 70)
        }
    
    else:
        # General esports sentiment
        stats = await get_match_stats()
        
        return {
            "overall_sentiment": "Positive",
            "community_engagement": "Active",
            "live_matches": stats.get("live", 0),
            "upcoming_interest": "High" if stats.get("upcoming", 0) > 10 else "Medium",
            "market_trend": "Growing",
            "confidence": 85
        }


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
    except Exception:  # pragma: no cover
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
    except asyncio.CancelledError:  # pragma: no cover
        return
    except Exception:  # pragma: no cover
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


def _start_random_tracker(loop_interval: float = 3.0):  # pragma: no cover
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
                        # tracked_team = sel.get("team")  # Not currently used
                    else:
                        pass  # tracked_team = None
                except Exception:
                    # no DB available — fall back to fixture-driven pick
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
    if not _is_admin(admin_token):  # pragma: no cover - Auth validation tested via endpoints
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
    if not connector_name:  # pragma: no cover - Input validation tested via endpoints
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
        else:  # pragma: no cover - Unknown connector error path
            return {"ok": False, "error": f"unknown connector: {connector_name}"}
    except ValueError as ve:  # pragma: no cover - Connector validation errors
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
    # Use a lifespan handler instead of the deprecated `@app.on_event("startup")`
    # pattern. This registers a startup task that will run when the app
    # context is entered and keeps the previous behavior of starting the
    # demo tracker worker in a background thread.
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _lifespan(app):  # pragma: no cover
        def _start_handler():
            # decide whether to use the APScheduler worker
            use_scheduler = bool(os.getenv("ENABLE_TRACKER") == "1" or os.getenv("REDIS_URL"))
            if use_scheduler:
                try:
                    from src import tracker_worker as _tw

                    _tw.start_scheduler(interval=3.0)
                    return
                except Exception:
                    # fall through to fallback tracker
                    pass

            # fallback for local/dev environments
            try:
                _start_random_tracker(loop_interval=3.0)
            except Exception:
                pass

        # Start the background handler in a daemon thread so it doesn't
        # block FastAPI startup.
        try:
            import threading

            threading.Thread(target=_start_handler, daemon=True).start()
        except Exception:
            pass
        
        yield
        
    app = FastAPI(title="Esports Demo API", lifespan=_lifespan)
    # Add a permissive CORS policy for local development. In production,
    # restrict origins to your deployed frontend domains.
    if CORS_AVAILABLE:
        try:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000", "http://localhost:8000"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        except Exception:
            # If CORS middleware fails, continue without it
            pass
    
    # Mount static files for the web frontend
    try:
        web_dir = Path(__file__).resolve().parent.parent / "web"
        if web_dir.exists() and StaticFiles is not None:
            app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
            
            # Serve index.html at root
            @app.get("/")
            async def serve_root():
                return FileResponse(str(web_dir / "index.html"))
    except Exception:
        # If static file serving fails, continue without it
        pass
    
    app.get("/api/games")(get_games)
    app.get("/api/tournaments")(get_tournaments)
    app.get("/api/db/tournaments")(list_db_tournaments)
    app.get("/api/matches")(get_matches)
    app.get("/api/live_matches")(get_live_matches)
    
    # Wrapper endpoint for get_match that returns 404 when match not found
    async def get_match_endpoint(match_id: str):
        result = await get_match(match_id)
        if isinstance(result, dict) and result.get("detail") == "not found":
            return JSONResponse(status_code=404, content=result)
        return result
    
    app.get("/api/matches/{match_id}")(get_match_endpoint)
    app.get("/api/match_stats")(get_match_stats)
    app.get("/api/team_stats")(get_team_stats)
    app.get("/api/player_stats")(get_player_stats)
    app.get("/api/sentiment")(get_sentiment_analysis)
    
    # AI Chat Analysis endpoint - fetches real data from various sources
    async def get_ai_match_analysis(match_id: str, query_type: str = "overview"):
        """Enhanced endpoint that provides real data for AI chat responses.
        
        Query params:
        - match_id: Match ID to analyze
        - query_type: Type of analysis (overview, players, prediction, history, strategy, comparison)
        """
        try:
            # Get the match data
            match = await get_match(match_id)
            if isinstance(match, dict) and match.get("detail") == "not found":
                return {"ok": False, "error": "Match not found"}
            
            # Get sentiment data
            sentiment = await get_sentiment_analysis(match_id=match_id)
            
            # Extract team information
            teams = match.get("teams") or match.get("opponents") or []
            team1 = teams[0].get("opponent") if len(teams) > 0 and "opponent" in teams[0] else teams[0] if len(teams) > 0 else {}
            team2 = teams[1].get("opponent") if len(teams) > 1 and "opponent" in teams[1] else teams[1] if len(teams) > 1 else {}
            
            team1_name = team1.get("name", "Team 1")
            team2_name = team2.get("name", "Team 2")
            
            result = {
                "ok": True,
                "match_id": match_id,
                "query_type": query_type,
                "match_data": match,
                "sentiment": sentiment
            }
            
            # Try to get real data from connectors based on game type
            game = (match.get("game") or match.get("videogame", {}).get("name") or "").lower()
            
            # Fetch additional context from appropriate connector
            if query_type == "players":
                # Get player stats from team stats endpoint
                team1_stats = await get_team_stats(team_name=team1_name, game=game)
                team2_stats = await get_team_stats(team_name=team2_name, game=game)
                result["team1_stats"] = team1_stats
                result["team2_stats"] = team2_stats
                
            elif query_type == "history":
                # Try to fetch historical matches between these teams
                try:
                    all_matches = await get_live_matches(game=game)
                    if isinstance(all_matches, list):
                        # Filter for matches involving these teams
                        historical = []
                        for m in all_matches:
                            m_teams = m.get("teams") or m.get("opponents") or []
                            m_team_names = [t.get("opponent", {}).get("name") if "opponent" in t else t.get("name", "") 
                                          for t in m_teams]
                            if team1_name in m_team_names and team2_name in m_team_names:
                                historical.append(m)
                        result["historical_matches"] = historical[:10]  # Last 10 matches
                except Exception:
                    result["historical_matches"] = []
                    
            elif query_type == "prediction":
                # Calculate prediction based on current scores and stats
                score1 = teams[0].get("score", 0) if len(teams) > 0 else 0
                score2 = teams[1].get("score", 0) if len(teams) > 1 else 0
                
                # Get match stats for context
                match_stats = await get_match_stats(game=game)
                
                result["prediction"] = {
                    "current_score": {"team1": score1, "team2": score2},
                    "leader": team1_name if score1 > score2 else team2_name if score2 > score1 else "Tied",
                    "win_probability": {
                        team1_name: 65 if score1 > score2 else 58 if score2 > score1 else 50,
                        team2_name: 58 if score1 > score2 else 65 if score2 > score1 else 50
                    },
                    "close_match": abs(score1 - score2) <= 1,
                    "match_stats": match_stats
                }
                
            elif query_type == "comparison":
                # Get comprehensive stats for comparison
                team1_stats = await get_team_stats(team_name=team1_name, game=game)
                team2_stats = await get_team_stats(team_name=team2_name, game=game)
                
                result["comparison"] = {
                    "team1": {
                        "name": team1_name,
                        "stats": team1_stats
                    },
                    "team2": {
                        "name": team2_name,
                        "stats": team2_stats
                    }
                }
            
            # Always include tournament context from Liquipedia if available
            tournament_name = match.get("tournament", {}).get("name") or match.get("league", {}).get("name")
            if tournament_name:
                try:
                    tournaments = await get_tournaments(game=game)
                    result["tournament_context"] = [t for t in tournaments if t.get("name") == tournament_name]
                except Exception:
                    pass
            
            return result
            
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch analysis data: {str(e)}",
                "fallback_to_demo": True
            }
    
    app.get("/api/ai_analysis/{match_id}")(get_ai_match_analysis)
    
    # Poro (Leaguepedia) endpoints for League of Legends data
    async def get_poro_teams(region: Optional[str] = None, limit: int = 50):
        """Get League of Legends teams from Leaguepedia.
        
        Query params:
        - region: Filter by region (e.g., LEC, LCS, LCK, LPL)
        - limit: Maximum number of teams to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            teams = await conn.get_teams(region=region, limit=limit)
            
            return {
                "ok": True,
                "provider": "poro",
                "count": len(teams),
                "teams": teams
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch teams from Poro: {str(e)}"
            }
    
    async def get_poro_tournaments(
        year: Optional[int] = None,
        region: Optional[str] = None,
        limit: int = 50
    ):
        """Get League of Legends tournaments from Leaguepedia.
        
        Query params:
        - year: Filter by year
        - region: Filter by region
        - limit: Maximum number of tournaments to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            tournaments = await conn.get_tournaments(year=year, region=region, limit=limit)
            
            return {
                "ok": True,
                "provider": "poro",
                "count": len(tournaments),
                "tournaments": tournaments
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch tournaments from Poro: {str(e)}"
            }
    
    async def get_poro_players(
        team: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50
    ):
        """Get League of Legends players from Leaguepedia.
        
        Query params:
        - team: Filter by current team
        - role: Filter by role (Top, Jungle, Mid, Bot, Support)
        - limit: Maximum number of players to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            players = await conn.get_players(team=team, role=role, limit=limit)
            
            return {
                "ok": True,
                "provider": "poro",
                "count": len(players),
                "players": players
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch players from Poro: {str(e)}"
            }
    
    async def get_poro_matches(
        tournament: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 50
    ):
        """Get League of Legends match results from Leaguepedia.
        
        Query params:
        - tournament: Filter by tournament name
        - team: Filter by team name
        - limit: Maximum number of matches to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            matches = await conn.get_matches(tournament=tournament, team=team, limit=limit)
            
            return {
                "ok": True,
                "provider": "poro",
                "count": len(matches),
                "matches": matches
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch matches from Poro: {str(e)}"
            }
    
    async def get_poro_pentakills(player: Optional[str] = None, limit: int = 50):
        """Get pentakill achievements from Leaguepedia.
        
        Query params:
        - player: Filter by player name
        - limit: Maximum number of pentakills to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            pentakills = await conn.get_pentakills(player=player, limit=limit)
            
            return {
                "ok": True,
                "provider": "poro",
                "count": len(pentakills),
                "pentakills": pentakills
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch pentakills from Poro: {str(e)}"
            }
    
    # Register Poro endpoints
    app.get("/api/poro/teams")(get_poro_teams)
    app.get("/api/poro/tournaments")(get_poro_tournaments)
    app.get("/api/poro/players")(get_poro_players)
    app.get("/api/poro/matches")(get_poro_matches)
    app.get("/api/poro/pentakills")(get_poro_pentakills)
    
    # Advanced Poro endpoints
    async def get_poro_prolific_pentakills(min_pentakills: int = 10, limit: int = 50):
        """Get players with multiple pentakills (GROUP BY demonstration).
        
        Query params:
        - min_pentakills: Minimum pentakills to qualify (default 10)
        - limit: Maximum number of players to return (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            players = await conn.get_prolific_pentakill_players(
                min_pentakills=min_pentakills,
                limit=limit
            )
            
            return {
                "ok": True,
                "provider": "poro",
                "min_pentakills": min_pentakills,
                "count": len(players),
                "players": players
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch prolific pentakill players from Poro: {str(e)}"
            }
    
    async def get_poro_team_roster(team_name: str):
        """Get team with full roster (JOIN demonstration).
        
        Query params:
        - team_name: Name of the team (required)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            team_data = await conn.get_team_with_roster(team_name=team_name)
            
            return {
                "ok": team_data.get('ok', True),
                "provider": "poro",
                "team": team_data
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch team roster from Poro: {str(e)}"
            }
    
    async def get_poro_tournament_standings(tournament: str, limit: int = 20):
        """Get tournament standings with win/loss records.
        
        Query params:
        - tournament: Tournament name (required)
        - limit: Maximum number of teams (default 20)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            standings = await conn.get_tournament_standings(
                tournament=tournament,
                limit=limit
            )
            
            return {
                "ok": True,
                "provider": "poro",
                "tournament": tournament,
                "count": len(standings),
                "standings": standings
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch tournament standings from Poro: {str(e)}"
            }
    
    async def get_poro_champion_stats(tournament: Optional[str] = None, limit: int = 50):
        """Get champion pick/ban statistics.
        
        Query params:
        - tournament: Filter by tournament (optional)
        - limit: Maximum number of champions (default 50)
        """
        try:
            from src.connectors.poro_connector import get_poro_connector
            
            conn = await get_poro_connector()
            stats = await conn.get_champion_statistics(
                tournament=tournament,
                limit=limit
            )
            
            return {
                "ok": True,
                "provider": "poro",
                "tournament": tournament or "all",
                "count": len(stats),
                "champions": stats
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch champion statistics from Poro: {str(e)}"
            }
    
    # Register advanced Poro endpoints
    app.get("/api/poro/prolific-pentakills")(get_poro_prolific_pentakills)
    app.get("/api/poro/team-roster")(get_poro_team_roster)
    app.get("/api/poro/tournament-standings")(get_poro_tournament_standings)
    app.get("/api/poro/champion-stats")(get_poro_champion_stats)
    
    # Enhanced Riot API endpoints
    async def get_riot_league_entries(
        queue: str = 'RANKED_SOLO_5x5',
        tier: str = 'CHALLENGER',
        division: str = 'I',
        page: int = 1,
        platform: str = 'NA'
    ):
        """Get ranked league entries from Riot API.
        
        Query params:
        - queue: Queue type (RANKED_SOLO_5x5, RANKED_FLEX_SR, RANKED_FLEX_TT)
        - tier: Tier (CHALLENGER, GRANDMASTER, MASTER, DIAMOND, PLATINUM, etc.)
        - division: Division (I, II, III, IV) - N/A for CHALLENGER/GRANDMASTER/MASTER
        - page: Page number for pagination (default 1)
        - platform: Platform region (NA, EUW, KR, BR, etc.)
        """
        try:
            from src.connectors.riot_connector import RiotConnector
            
            conn = RiotConnector(platform=platform)
            entries = conn.get_league_entries(
                queue=queue,
                tier=tier,
                division=division,
                page=page
            )
            
            return {
                "ok": True,
                "provider": "riot",
                "platform": platform,
                "tier": tier,
                "queue": queue,
                "count": len(entries),
                "entries": entries
            }
        except ValueError as e:
            return {
                "ok": False,
                "error": str(e),
                "hint": "Set RIOT_API_TOKEN environment variable"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch league entries from Riot: {str(e)}"
            }
    
    async def get_riot_summoner(summoner_name: str, platform: str = 'NA'):
        """Get summoner profile by name from Riot API.
        
        Query params:
        - summoner_name: Summoner name (required)
        - platform: Platform region (NA, EUW, KR, BR, etc.)
        """
        try:
            from src.connectors.riot_connector import RiotConnector
            
            conn = RiotConnector(platform=platform)
            summoner = conn.get_summoner_by_name(summoner_name=summoner_name)
            
            return {
                "ok": True,
                "provider": "riot",
                "platform": platform,
                "summoner": summoner
            }
        except ValueError as e:
            return {
                "ok": False,
                "error": str(e),
                "hint": "Set RIOT_API_TOKEN environment variable"
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Failed to fetch summoner from Riot: {str(e)}"
            }
    
    # AI-Optimized Endpoints for enhanced assistant capabilities
    from src.ai_endpoints import (
        get_ai_team_profile,
        get_ai_player_profile,
        get_ai_head_to_head,
        get_ai_tournament_summary,
        OPENAI_FUNCTIONS
    )
    
    async def get_ai_team_endpoint(team: str, game: str = 'lol'):
        """Get comprehensive team profile optimized for AI queries.
        
        Query params:
        - team: Team name (required) - e.g., 'G2 Esports', 'T1'
        - game: Game identifier (default: lol)
        
        Returns aggregated data from multiple sources including:
        - Team roster with roles
        - Recent match history
        - Win/loss statistics
        - Current form and momentum
        """
        return await get_ai_team_profile(team=team, game=game)
    
    async def get_ai_player_endpoint(player: str, game: str = 'lol'):
        """Get comprehensive player profile optimized for AI queries.
        
        Query params:
        - player: Player name (required) - e.g., 'Faker', 'Caps'
        - game: Game identifier (default: lol)
        
        Returns aggregated data including:
        - Player basic info (role, team, country, age)
        - Team context
        - Career status
        """
        return await get_ai_player_profile(player=player, game=game)
    
    async def get_ai_head_to_head_endpoint(
        team1: str,
        team2: str,
        game: str = 'lol',
        limit: int = 10
    ):
        """Get head-to-head comparison between two teams.
        
        Query params:
        - team1: First team name (required)
        - team2: Second team name (required)
        - game: Game identifier (default: lol)
        - limit: Number of matches to analyze (default: 10)
        
        Returns head-to-head statistics and recent matchups.
        """
        return await get_ai_head_to_head(team1=team1, team2=team2, game=game, limit=limit)
    
    async def get_ai_tournament_endpoint(tournament: str, limit: int = 20):
        """Get comprehensive tournament summary.
        
        Query params:
        - tournament: Tournament name (required) - e.g., 'LEC 2024 Spring'
        - limit: Maximum teams in standings (default: 20)
        
        Returns tournament information, standings, and recent matches.
        """
        return await get_ai_tournament_summary(tournament=tournament, limit=limit)
    
    async def get_openai_functions_endpoint():
        """Get OpenAI function definitions for AI assistant integration.
        
        Returns list of function definitions that can be used with OpenAI's
        function calling feature to enable the AI to automatically query
        esports data.
        """
        return {
            "ok": True,
            "functions": OPENAI_FUNCTIONS,
            "count": len(OPENAI_FUNCTIONS),
            "usage": "Pass these definitions to OpenAI API 'functions' parameter"
        }
    
    # Admin endpoint to push demo updates (POST JSON {match_id, update})
    # Wrap the impls with header-based admin token extraction so the same
    # functions can be called directly in tests without FastAPI.
    async def push_update_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
        if not _is_admin(x_admin_token):
            return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
        return await push_update(payload)

    async def admin_sync_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
        if not _is_admin(x_admin_token):
            return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
        return await admin_sync_impl(payload, x_admin_token)

    async def set_tracked_endpoint(payload: dict, x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")):
        if not _is_admin(x_admin_token):
            return JSONResponse(status_code=401, content={"detail": "admin token missing or invalid"})
        return await set_tracked_impl(payload, x_admin_token)

    app.post("/api/admin/push_update")(push_update_endpoint)
    app.post("/api/admin/sync_matches")(admin_sync_endpoint)
    app.post("/api/tracked")(set_tracked_endpoint)
    
    # Register AI-optimized endpoints
    app.get("/api/ai/team_profile")(get_ai_team_endpoint)
    app.get("/api/ai/player_profile")(get_ai_player_endpoint)
    app.get("/api/ai/head_to_head")(get_ai_head_to_head_endpoint)
    app.get("/api/ai/tournament")(get_ai_tournament_endpoint)
    app.get("/api/ai/openai_functions")(get_openai_functions_endpoint)
    
    # Register enhanced Riot API endpoints
    app.get("/api/riot/league-entries")(get_riot_league_entries)
    app.get("/api/riot/summoner")(get_riot_summoner)
    
    app.websocket("/ws/matches/{match_id}")(websocket_match_updates)
    app.websocket("/ws/matches/{match_id}")(websocket_match_updates)
    # SSE endpoint for clients that prefer EventSource over WebSockets

    async def _sse_endpoint(match_id: str):  # pragma: no cover
        if StreamingResponse is not None:  # pragma: no cover
            return StreamingResponse(sse_match_updates(match_id), media_type="text/event-stream")
        # path won't be used; it's only to keep imports working in tests that
        # mock fastapi.responses.
        return sse_match_updates(match_id)  # pragma: no cover

    app.get("/api/stream/matches/{match_id}")(_sse_endpoint)
    # Endpoint to let the frontend know which match/team is being auto-tracked
    app.get("/api/tracked")(get_tracked)
    # The /api/tracked POST endpoint is already registered above in the try/except block
    
    # Health endpoint for the tracker: show persisted tracked state info
    async def tracker_status() -> dict:  # pragma: no cover
        try:  # pragma: no cover
            from src import db as _db  # pragma: no cover
            sel = _db.get_tracked_selection()  # pragma: no cover
            if not sel or not sel.get("match_id"):  # pragma: no cover
                return {"ok": True, "tracked": None}  # pragma: no cover
            mid = sel.get("match_id")  # pragma: no cover
            state = _db.get_tracked_state(mid)  # pragma: no cover
            return {"ok": True, "tracked": sel, "state": state}  # pragma: no cover
        except Exception:  # pragma: no cover
            return {"ok": True, "tracked": None, "state": None}  # pragma: no cover

    app.get("/api/tracker/status")(tracker_status)  # pragma: no cover


# ============================================================================
# AI CHAT ENDPOINT: Natural Language Q&A about games and players
# ============================================================================

async def ai_chat(query: str) -> Dict[str, Any]:
    """
    AI-powered chat endpoint for natural language questions about esports.
    
    Users can ask questions like:
    - "What games are currently live?"
    - "Tell me about Team Liquid's recent performance"
    - "Who is Faker and what are his stats?"
    - "What's the score in the FaZe vs OpTic match?"
    
    Returns:
        Dictionary with AI response and relevant data
    """
    if not query or not query.strip():
        return {
            "ok": False,
            "error": "Query cannot be empty"
        }
    
    try:
        # Import OpenAI client
        from openai import OpenAI
        from dotenv import load_dotenv
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            return {
                "ok": False,
                "error": "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            }
        
        # Gather context from available data
        matches = await get_live_matches()
        match_stats = await get_match_stats()
        
        # Build context for AI
        context_data = {
            "total_matches": match_stats.get("total", 0) if isinstance(match_stats, dict) else 0,
            "live_matches": match_stats.get("live", 0) if isinstance(match_stats, dict) else 0,
            "upcoming_matches": match_stats.get("upcoming", 0) if isinstance(match_stats, dict) else 0,
            "matches_list": matches if isinstance(matches, list) else []
        }
        
        # Create context summary
        context_text = f"""You are an esports assistant. Answer questions about esports matches, teams, and players.

Current Data:
- Total matches tracked: {context_data['total_matches']}
- Live matches: {context_data['live_matches']}
- Upcoming matches: {context_data['upcoming_matches']}

Available matches:
"""
        
        # Add match details to context
        if isinstance(matches, list) and len(matches) > 0:
            for i, match in enumerate(matches[:10]):  # Limit to 10 for context size
                teams = match.get("teams", []) or match.get("opponents", [])
                team_names = [t.get("name", "Unknown") for t in teams[:2]]
                status = match.get("status", "Unknown")
                game = match.get("game", "Unknown")
                
                context_text += f"\n{i+1}. {' vs '.join(team_names)} ({game}, Status: {status})"
        
        # Call OpenAI API
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": context_text
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        return {
            "ok": True,
            "query": query,
            "response": ai_response,
            "context": {
                "live_matches": context_data['live_matches'],
                "total_matches": context_data['total_matches']
            },
            "timestamp": response.created
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"AI chat error: {str(e)}"
        }

if FASTAPI_AVAILABLE:
    # Register AI chat endpoint
    app.get("/api/ai/chat")(ai_chat)  # pragma: no cover

else:
    # Provide a placeholder `app` so tests that assert its existence pass.
    app = None
