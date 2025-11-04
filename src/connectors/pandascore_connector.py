"""Simple PandaScore connector.

This is a minimal, safe-to-import connector that encapsulates calls to the
PandaScore REST API. It deliberately avoids making network calls at import
time. To use it, set the `PANDASCORE_TOKEN` environment variable and call
`PandaScoreConnector.get_matches()`.

Notes/assumptions:
- Uses HTTPX for requests (sync client). The token is sent as an
  Authorization: Bearer <token> header.
- This module implements a small normalization to a minimal match shape
  used by the demo app: {id, title, scheduled_time, teams}
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx


class PandaScoreConnector:
    """Connector for PandaScore API with light hardening.

    - Accepts token optionally at construction time (useful for tests).
    - Performs simple retry/backoff on network errors.
    - Normalizes match responses to a minimal shape used by the demo.

    Note: Raises ValueError from get_matches() if no token is configured.
    """

    BASE_URL = "https://api.pandascore.co"

    def __init__(self, token: Optional[str] = None, timeout: float = 10.0, max_retries: int = 2):
        # token may be None for test-time instantiation; get_matches will validate.
        self.token = token or os.getenv("PANDASCORE_TOKEN")
        self.timeout = timeout
        self.max_retries = max_retries
        # create client lazily to avoid side-effects at import-time in tests
        # type: ignore - runtime assignment without explicit annotation
        self._client = None

    def _client_instance(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _headers(self) -> Dict[str, str]:
        # Small helper: return headers for requests.
        return {"Authorization": f"Bearer {self.token}"}

    def get_matches(self, game: Optional[str] = None, per_page: int = 25, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch and normalize matches.

        Args:
            game: Filter by video game (e.g., 'lol', 'csgo', 'dota2')
            per_page: Number of results per page (max 100)
            status: Filter by status ('running', 'not_started', 'finished')

        Raises ValueError if no token is configured.
        """
        if not self.token:
            raise ValueError("PANDASCORE_TOKEN must be set to fetch matches")

        # Use more results per page and sort by begin_at to get most relevant matches
        params: Dict[str, Any] = {
            "page[size]": min(per_page, 100),  # PandaScore max is 100
            "sort": "-begin_at",  # Sort by start time descending (most recent first)
        }
        
        if game:
            # PandaScore uses lowercase game slugs
            game_slug = game.lower().replace('-', '').replace('_', '')
            if game_slug == 'csgo':
                game_slug = 'cs-go'
            elif game_slug == 'lol':
                game_slug = 'league-of-legends'
            elif game_slug == 'dota2':
                game_slug = 'dota-2'
            params["filter[videogame]"] = game_slug
        
        if status:
            params["filter[status]"] = status

        # For live matches, use the running endpoint for better results
        if status == 'running':
            url = f"{self.BASE_URL}/matches/running"
        else:
            url = f"{self.BASE_URL}/matches"
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, headers=self._headers(), params=params)
                # Respect 429 Retry-After when present and retry accordingly.
                if getattr(resp, "status_code", None) == 429:
                    ra = None
                    try:
                        ra = int(getattr(resp, "headers", {}).get("Retry-After") or 0)
                    except Exception:
                        ra = 0
                    if ra and attempt < self.max_retries:
                        time.sleep(ra)
                        continue
                    # else let it fall through to raise below

                resp.raise_for_status()
                data = resp.json()
                break
            except Exception:
                # simple backoff for non-429 errors
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

        normalized: List[Dict[str, Any]] = []
        for item in data:
            match_id = item.get("id")
            opponents = []
            for team in item.get("opponents") or []:
                t = team.get("opponent") or {}
                opponents.append(t.get("name") or t.get("slug") or "unknown")

            title = item.get("name") or " vs ".join(opponents) or f"match-{match_id}"
            scheduled = item.get("scheduled_at") or item.get("begin_at")

            teams = []
            for team in item.get("opponents") or []:
                t = team.get("opponent") or {}
                # Get score from the results
                results = item.get("results") or []
                score = None
                if results and len(results) > len(teams):
                    result = results[len(teams)]
                    score = result.get("score") if isinstance(result, dict) else None
                
                teams.append({
                    "id": t.get("id"), 
                    "name": t.get("name"),
                    "acronym": t.get("acronym"),
                    "score": score
                })

            # Extract video game information
            video_game_data = item.get("videogame") or item.get("video_game") or {}
            video_game_name = video_game_data.get("name") if isinstance(video_game_data, dict) else str(video_game_data) if video_game_data else None
            
            # Get league/tournament info
            league_data = item.get("league") or {}
            tournament_data = item.get("tournament") or item.get("serie") or {}
            
            # Get stream information
            streams = item.get("streams_list") or item.get("streams") or []
            stream_url = None
            if streams and len(streams) > 0:
                stream_url = streams[0].get("raw_url") or streams[0].get("embed_url")

            normalized.append({
                "id": match_id,
                "title": title,
                "scheduled_time": scheduled,
                "begin_at": item.get("begin_at"),
                # PandaScore returns a status field like "running", "finished",
                # include it when present so callers can filter by status.
                "status": item.get("status"),
                "teams": teams,
                "opponents": [{"opponent": team} for team in teams],  # For compatibility
                "video_game": video_game_name,
                "videogame": {"name": video_game_name, "slug": video_game_data.get("slug")} if video_game_name else None,
                "game": video_game_name,
                "provider": "PandaScore",
                "league": {"name": league_data.get("name"), "id": league_data.get("id")} if league_data else None,
                "tournament": {"name": tournament_data.get("name"), "id": tournament_data.get("id")} if tournament_data else None,
                "match_type": item.get("match_type") or item.get("number_of_games"),
                "streams_list": streams,
                "stream_url": stream_url,
                "results": item.get("results"),
                "games": item.get("games"),
            })

        return normalized
