"""Battlefy API connector for tournament and match data.

Battlefy is a popular esports tournament platform that provides
APIs for accessing tournament brackets and match information.

API Documentation: https://developers.battlefy.com/
"""
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx


class BattlefyConnector:
    """Connector for Battlefy API to fetch tournament match data."""

    BASE_URL = "https://api.battlefy.com"
    
    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        """Initialize the Battlefy connector.

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
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        self._last_request_time = time.time()

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch matches from Battlefy tournaments.

        Args:
            game: Optional game filter (valorant, lol, csgo, etc.)
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        # For demo purposes, return structured sample data
        # In production, this would call Battlefy's API endpoints
        
        normalized: List[Dict[str, Any]] = []
        
        # Generate sample Battlefy tournament matches
        sample_tournaments = [
            ("Valorant Champions Tour", "valorant", [("Sentinels", "100 Thieves")]),
            ("League of Legends Clash", "lol", [("Team SoloMid", "Counter Logic Gaming")]),
            ("CS:GO Open Series", "csgo", [("Evil Geniuses", "Team Envy")]),
            ("Dota 2 Pro Circuit", "dota2", [("OG", "Team Secret")]),
            ("Overwatch Contenders", "overwatch", [("San Francisco Shock", "Dallas Fuel")])
        ]
        
        for i, (tournament, game_name, matches) in enumerate(sample_tournaments):
            # Filter by game if specified
            if game and game.lower() not in game_name.lower():
                continue
                
            for j, (team1, team2) in enumerate(matches):
                match_id = f"battlefy_{i}_{j}"
                
                # Vary status for demo
                if i == 0 and j == 0:
                    status = "live"
                    team1_score = 2
                    team2_score = 1
                elif i == 1:
                    status = "upcoming"
                    team1_score = 0
                    team2_score = 0
                else:
                    status = "finished"
                    team1_score = 3
                    team2_score = 1
                
                game_display = {
                    "valorant": "Valorant",
                    "lol": "League of Legends",
                    "csgo": "Counter-Strike: GO",
                    "dota2": "Dota 2",
                    "overwatch": "Overwatch"
                }.get(game_name, game_name.title())
                
                normalized.append({
                    "id": match_id,
                    "title": f"{tournament}: {team1} vs {team2}",
                    "name": f"{team1} vs {team2}",
                    "tournament": tournament,
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
                    "video_game": game_display,
                    "game": game_name,
                    "provider": "Battlefy",
                    "source": "battlefy",
                    "url": f"https://battlefy.com/match/{match_id}"
                })
                
                if len(normalized) >= limit:
                    return normalized
        
        return normalized[:limit]

    def close(self):
        """Close the HTTP client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
