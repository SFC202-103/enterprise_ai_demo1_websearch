from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx


class RiotConnector:
    """Minimal Riot Games connector skeleton.

    This connector mirrors the PandaScore connector's external shape for the
    demo: accept optional token at construction, lazy httpx client, retries,
    and normalize responses into the demo's minimal match shape.

    NOTE: Riot's real API requires specific endpoints and routing by region
    and API key formats. This class provides a simple shape suitable for
    testing and local development; extend it for production usage.
    """

    # Riot API base is region-dependent; leave as placeholder
    BASE_URL = "https://api.riotgames.com"

    def __init__(self, token: Optional[str] = None, timeout: float = 10.0, max_retries: int = 2):
        self.token = token or os.getenv("RIOT_API_TOKEN")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None

    def _client_instance(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _headers(self) -> Dict[str, str]:
        return {"X-Riot-Token": self.token} if self.token else {}

    def get_matches(self, game: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetch and normalize match-like objects from Riot.

        Raises ValueError if no token is configured.
        For the demo we call a placeholder endpoint. Tests should mock
        httpx responses rather than hitting a real Riot API.
        """
        if not self.token:
            raise ValueError("RIOT_API_TOKEN must be set to fetch matches")

        # Placeholder endpoint path — tests will mock the HTTP call
        url = f"{self.BASE_URL}/lol/matches/v1/matches"

        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                params = {"limit": limit}
                resp = client.get(url, headers=self._headers(), params=params)
                # Handle rate-limiting if Riot responds with 429 and Retry-After
                if getattr(resp, "status_code", None) == 429:
                    ra = None
                    try:
                        ra = int(getattr(resp, "headers", {}).get("Retry-After") or 0)
                    except Exception:
                        ra = 0
                    if ra and attempt < self.max_retries:
                        time.sleep(ra)
                        continue

                resp.raise_for_status()
                data = resp.json()
                break
            except Exception:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

        normalized: List[Dict[str, Any]] = []
        for item in data:
            match_id = item.get("id")
            title = item.get("gameName") or item.get("metadata", {}).get("name") or f"match-{match_id}"
            scheduled = item.get("scheduled_at") or item.get("startTime")
            teams = []
            for t in item.get("teams") or []:
                teams.append({"id": t.get("id"), "name": t.get("name")})

            normalized.append({
                "id": match_id,
                "title": title,
                "scheduled_time": scheduled,
                # Riot may expose various status/state fields; include a best-effort
                # status value when present so callers can filter by live/upcoming.
                "status": item.get("status") or item.get("state"),
                "teams": teams,
            })

        return normalized
