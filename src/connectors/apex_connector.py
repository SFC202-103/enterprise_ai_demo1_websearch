"""Apex Legends API connector for match and player data.

This connector integrates with Apex Legends game data sources.
Note: Apex Legends doesn't have an official comprehensive API,
so this uses community APIs and tracking sites.

Potential sources:
- https://apexlegendsapi.com/ (unofficial API)
- https://apex.tracker.gg/ (tracker network)
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import random

import httpx


class ApexLegendsConnector:
    """Connector for Apex Legends match and tournament data."""

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        """Initialize the Apex Legends connector.

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
                "User-Agent": "EsportsDemo/1.0",
                "Accept": "application/json"
            }
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch Apex Legends tournament and competitive matches.

        Args:
            game: Ignored (always Apex Legends)
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        # For demo purposes, return structured sample data
        # In production, integrate with apex.tracker.gg or ALGS API
        
        normalized: List[Dict[str, Any]] = []
        
        # Sample Apex Legends professional teams
        sample_teams = [
            ("TSM", "DarkZero"),
            ("OpTic Gaming", "NRG Esports"),
            ("Team Liquid", "FURIA Esports"),
            ("100 Thieves", "Sentinels"),
            ("Cloud9", "G2 Esports")
        ]
        
        tournaments = [
            "ALGS Championship",
            "ALGS Pro League",
            "Apex Legends Global Series",
            "Split 1 Playoffs",
            "Regional Finals"
        ]
        
        for i, (team1, team2) in enumerate(sample_teams[:min(limit, 5)]):
            match_id = f"apex_{i+1}"
            tournament = tournaments[i % len(tournaments)]
            
            # Vary status for demo
            if i == 0:
                status = "live"
                team1_score = 125
                team2_score = 108
            elif i == 1:
                status = "upcoming"
                team1_score = 0
                team2_score = 0
                scheduled = datetime.now() + timedelta(hours=2+i)
            else:
                status = "finished"
                team1_score = random.randint(80, 150)
                team2_score = random.randint(80, 150)
                scheduled = datetime.now() - timedelta(hours=i)
            
            if i < 2:
                scheduled = datetime.now() + timedelta(hours=2+i)
            else:
                scheduled = datetime.now() - timedelta(hours=i)
            
            normalized.append({
                "id": match_id,
                "title": f"{tournament}: {team1} vs {team2}",
                "name": f"{team1} vs {team2}",
                "tournament": tournament,
                "scheduled_time": scheduled.isoformat(),
                "scheduled_at": scheduled.isoformat(),
                "status": status,
                "live": status == "live",
                "teams": [
                    {
                        "name": team1,
                        "acronym": team1,
                        "score": team1_score if status != "upcoming" else None
                    },
                    {
                        "name": team2,
                        "acronym": team2,
                        "score": team2_score if status != "upcoming" else None
                    }
                ],
                "opponents": [
                    {
                        "name": team1,
                        "acronym": team1,
                        "score": team1_score if status != "upcoming" else None
                    },
                    {
                        "name": team2,
                        "acronym": team2,
                        "score": team2_score if status != "upcoming" else None
                    }
                ],
                "video_game": "Apex Legends",
                "game": "apex",
                "provider": "Apex Tracker",
                "source": "apex",
                "url": f"https://apex.tracker.gg/match/{match_id}"
            })
        
        return normalized[:limit]

    def close(self):
        """Close the HTTP client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
