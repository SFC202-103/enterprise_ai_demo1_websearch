"""HLTV.org connector for CS:GO esports data.

HLTV is the leading source for CS:GO competitive matches and statistics.
This connector fetches match data from HLTV.

Note: HLTV doesn't have an official public API, so this uses web scraping
or unofficial API endpoints. In production, ensure compliance with their terms.
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx


class HLTVConnector:
    """Connector for HLTV.org to fetch CS:GO match data."""

    BASE_URL = "https://www.hltv.org"
    
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        """Initialize the HLTV connector.

        Args:
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None
        self._last_request_time = 0.0

    def _client_instance(self) -> httpx.Client:
        """Get or create HTTP client instance."""
        if self._client is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json, text/html"
            }
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client

    def _rate_limit(self):
        """Enforce rate limiting to be respectful to the server."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch CS:GO matches from HLTV.

        Args:
            game: Ignored (always CS:GO for HLTV)
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        # For demo purposes, return structured sample data
        # In production, this would scrape or call HLTV's endpoints
        
        normalized: List[Dict[str, Any]] = []
        
        # Generate sample HLTV matches
        sample_teams = [
            ("FaZe Clan", "Natus Vincere"),
            ("Team Vitality", "G2 Esports"),
            ("Heroic", "ENCE"),
            ("Cloud9", "Team Liquid"),
            ("FURIA", "Imperial")
        ]
        
        for i, (team1, team2) in enumerate(sample_teams[:min(limit, 5)]):
            match_id = f"hltv_{i+1}"
            
            # Vary status for demo
            if i == 0:
                status = "live"
                team1_score = 13
                team2_score = 11
            elif i == 1:
                status = "upcoming"
                team1_score = 0
                team2_score = 0
            else:
                status = "finished"
                team1_score = 16
                team2_score = 12 + i
            
            normalized.append({
                "id": match_id,
                "title": f"{team1} vs {team2}",
                "name": f"{team1} vs {team2}",
                "scheduled_time": datetime.now().isoformat(),
                "scheduled_at": datetime.now().isoformat(),
                "status": status,
                "live": status == "live",
                "teams": [
                    {
                        "name": team1,
                        "acronym": team1.split()[0],
                        "score": team1_score if status != "upcoming" else None
                    },
                    {
                        "name": team2,
                        "acronym": team2.split()[0],
                        "score": team2_score if status != "upcoming" else None
                    }
                ],
                "opponents": [
                    {
                        "name": team1,
                        "acronym": team1.split()[0],
                        "score": team1_score if status != "upcoming" else None
                    },
                    {
                        "name": team2,
                        "acronym": team2.split()[0],
                        "score": team2_score if status != "upcoming" else None
                    }
                ],
                "video_game": "Counter-Strike: GO",
                "game": "csgo",
                "provider": "HLTV",
                "source": "hltv",
                "url": f"https://www.hltv.org/matches/{match_id}"
            })
        
        return normalized[:limit]

    def close(self):
        """Close the HTTP client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
