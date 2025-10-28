"""OpenDota API connector for Dota 2 professional match data.

OpenDota provides free access to comprehensive Dota 2 data including
professional matches, player statistics, and tournament information.

API Documentation: https://docs.opendota.com/
"""
import time
from typing import Any, Dict, List, Optional

import httpx


class OpenDotaConnector:
    """Connector for OpenDota API to fetch Dota 2 professional match data."""

    BASE_URL = "https://api.opendota.com/api"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        """Initialize the OpenDota connector.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None

    def _client_instance(self) -> httpx.Client:
        """Get or create HTTP client instance."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def get_pro_matches(self, less_than_match_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch professional Dota 2 matches.

        Args:
            less_than_match_id: Fetch matches with ID less than this value (for pagination)

        Returns:
            List of normalized match dictionaries
        """
        params: Dict[str, Any] = {}
        if less_than_match_id:
            params["less_than_match_id"] = less_than_match_id

        url = f"{self.BASE_URL}/proMatches"
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, params=params)

                # Handle rate limiting
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue

                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

        # Normalize the response to match our standard format
        normalized: List[Dict[str, Any]] = []
        for match in data:
            # OpenDota returns matches with basic info, need to fetch details for teams
            match_id = match.get("match_id")
            
            # Extract team information
            radiant_name = match.get("radiant_name") or "Radiant"
            dire_name = match.get("dire_name") or "Dire"
            radiant_team_id = match.get("radiant_team_id")
            dire_team_id = match.get("dire_team_id")
            
            # Determine winner (radiant_win is boolean)
            radiant_win = match.get("radiant_win", False)
            radiant_score = 1 if radiant_win else 0
            dire_score = 0 if radiant_win else 1

            teams = [
                {
                    "id": radiant_team_id,
                    "name": radiant_name,
                    "acronym": radiant_name[:4].upper() if radiant_name else "RAD",
                    "score": radiant_score
                },
                {
                    "id": dire_team_id,
                    "name": dire_name,
                    "acronym": dire_name[:4].upper() if dire_name else "DIRE",
                    "score": dire_score
                }
            ]

            # Convert start_time (Unix timestamp) to ISO format
            start_time = match.get("start_time")
            scheduled_time = None
            if start_time:
                from datetime import datetime
                scheduled_time = datetime.fromtimestamp(start_time).isoformat() + "Z"

            # Match is finished if we have a winner
            status = "finished" if match.get("radiant_win") is not None else "unknown"

            # Get league/tournament info
            league_name = match.get("league_name", "")
            series_type = match.get("series_type", 0)  # 0=bo1, 1=bo3, 2=bo5
            
            title = f"{radiant_name} vs {dire_name}"
            if league_name:
                title = f"{league_name}: {title}"

            normalized.append({
                "id": match_id,
                "title": title,
                "scheduled_time": scheduled_time,
                "status": status,
                "teams": teams,
                "video_game": "Dota 2",
                "game": "Dota 2",
                "provider": "OpenDota",
                "league_id": match.get("leagueid"),
                "league_name": league_name,
                "series_type": series_type,
                "duration": match.get("duration"),  # Match duration in seconds
            })

        return normalized

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch matches with pagination limit.

        Args:
            game: Unused, always returns Dota 2 matches
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        matches = self.get_pro_matches()
        return matches[:limit] if limit else matches

    def get_match_details(self, match_id: int) -> Dict[str, Any]:
        """Fetch detailed information about a specific match.

        Args:
            match_id: The match ID to fetch details for

        Returns:
            Detailed match information
        """
        url = f"{self.BASE_URL}/matches/{match_id}"
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url)
                
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    def close(self):
        """Close the HTTP client connection."""
        if self._client:
            self._client.close()
            self._client = None

    def __del__(self):
        """Cleanup HTTP client on deletion."""
        self.close()
