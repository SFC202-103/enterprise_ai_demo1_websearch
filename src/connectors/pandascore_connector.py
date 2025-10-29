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

    def get_matches(self, game: Optional[str] = None, per_page: int = 25) -> List[Dict[str, Any]]:
        """Fetch and normalize matches.

        Raises ValueError if no token is configured.
        """
        if not self.token:
            raise ValueError("PANDASCORE_TOKEN must be set to fetch matches")

        params: Dict[str, Any] = {"page[size]": per_page}
        if game:
            params["filter[video_game]"] = game

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

            normalized.append({
                "id": match_id,
                "title": title,
                "scheduled_time": scheduled,
                # PandaScore returns a status field like "running", "finished",
                # include it when present so callers can filter by status.
                "status": item.get("status"),
                "teams": teams,
                "video_game": video_game_name,
                "game": video_game_name,
                "provider": "PandaScore",
            })

        return normalized
