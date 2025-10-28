"""Riot Games LoL Esports API connector.

Provides access to official League of Legends esports tournament data,
including live matches, schedules, and historical results.

API endpoints discovered from: https://esports-api.lolesports.com/
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx


class RiotEsportsConnector:
    """Connector for Riot Games LoL Esports API."""

    BASE_URL = "https://esports-api.lolesports.com/persisted/gw"
    FEED_URL = "https://feed.lolesports.com/livestats/v1"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        """Initialize the Riot Esports connector.

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
            # Riot API requires specific headers
            headers = {
                "x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z",  # Public API key from esports site
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client

    def get_schedule(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch the esports schedule.

        Args:
            league_id: Optional league ID to filter by specific league

        Returns:
            List of scheduled events and matches
        """
        url = f"{self.BASE_URL}/getSchedule"
        params: Dict[str, str] = {"hl": "en-US"}
        if league_id:
            params["leagueId"] = league_id

        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, params=params)
                
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", {}).get("schedule", {}).get("events", [])
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    def get_live(self) -> List[Dict[str, Any]]:
        """Fetch currently live matches.

        Returns:
            List of live matches
        """
        url = f"{self.BASE_URL}/getLive"
        params: Dict[str, str] = {"hl": "en-US"}

        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, params=params)
                
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", {}).get("schedule", {}).get("events", [])
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch League of Legends esports matches.

        Args:
            game: Unused, always returns LoL matches
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        # Fetch both live and scheduled matches
        events = []
        
        try:
            events.extend(self.get_live())
        except Exception:
            pass  # Continue even if live fetch fails
        
        try:
            scheduled = self.get_schedule()
            events.extend(scheduled)
        except Exception:
            pass
        
        # Normalize the response
        normalized: List[Dict[str, Any]] = []
        
        for event in events[:limit]:
            # Extract match information from event
            match_data = event.get("match", {})
            event_id = event.get("id", "")
            
            # Get teams
            teams_data = match_data.get("teams", [])
            teams = []
            
            for team_data in teams_data:
                team_name = team_data.get("name", "Unknown")
                team_code = team_data.get("code", team_name[:3].upper())
                team_result = team_data.get("result", {})
                
                # Extract score from result
                game_wins = team_result.get("gameWins", 0)
                
                teams.append({
                    "id": team_data.get("id"),
                    "name": team_name,
                    "acronym": team_code,
                    "score": game_wins
                })
            
            # Determine status
            state = event.get("state", "unstarted")
            status_map = {
                "unstarted": "upcoming",
                "inProgress": "live",
                "completed": "finished"
            }
            status = status_map.get(state, "upcoming")
            
            # Get scheduled time
            start_time = event.get("startTime")
            scheduled_time = start_time if start_time else None
            
            # Build title
            league_name = event.get("league", {}).get("name", "")
            tournament_name = event.get("blockName", "")
            
            if teams and len(teams) >= 2:
                title = f"{teams[0]['name']} vs {teams[1]['name']}"
            else:
                title = f"Match {event_id}"
            
            if league_name:
                title = f"{league_name}: {title}"
            if tournament_name and tournament_name not in title:
                title = f"{title} ({tournament_name})"
            
            normalized.append({
                "id": event_id,
                "title": title,
                "scheduled_time": scheduled_time,
                "status": status,
                "teams": teams,
                "video_game": "League of Legends",
                "game": "League of Legends",
                "provider": "Riot Esports",
                "league": event.get("league", {}).get("name"),
                "league_id": event.get("league", {}).get("id"),
                "tournament": tournament_name,
                "match_type": match_data.get("strategy", {}).get("type"),
            })
        
        return normalized

    def get_event_details(self, event_id: str) -> Dict[str, Any]:
        """Fetch detailed information about a specific event.

        Args:
            event_id: The event ID to fetch details for

        Returns:
            Detailed event information
        """
        url = f"{self.BASE_URL}/getEventDetails"
        params = {"hl": "en-US", "id": event_id}
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, params=params)
                
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                
                resp.raise_for_status()
                return resp.json().get("data", {})
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
