"""Liquipedia MediaWiki API connector for esports data.

Liquipedia is a comprehensive esports wiki with historical match data
across all major esports titles. This connector uses the MediaWiki API
to fetch structured data from Liquipedia pages.

API Documentation: https://liquipedia.net/api-terms-of-use
MediaWiki API: https://www.mediawiki.org/wiki/API:Main_page

Note: Must comply with Liquipedia API terms:
- Include proper User-Agent with contact information
- Respect rate limits (max 1 request per 2 seconds)
- Provide attribution when displaying data
"""
import time
from typing import Any, Dict, List, Optional
import re

import httpx


class LiquipediaConnector:
    """Connector for Liquipedia MediaWiki API to fetch esports data."""

    # Base URLs for different esports
    WIKI_URLS = {
        "dota2": "https://liquipedia.net/dota2/api.php",
        "lol": "https://liquipedia.net/leagueoflegends/api.php",
        "csgo": "https://liquipedia.net/counterstrike/api.php",
        "valorant": "https://liquipedia.net/valorant/api.php",
        "overwatch": "https://liquipedia.net/overwatch/api.php",
    }

    def __init__(
        self, 
        game: str = "csgo",
        user_agent: str = "EsportsDemo/1.0 (contact@example.com)",
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        """Initialize the Liquipedia connector.

        Args:
            game: Game to fetch data for (dota2, lol, csgo, valorant, overwatch)
            user_agent: User agent string with contact info (REQUIRED by Liquipedia)
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.game = game.lower()
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None
        self._last_request_time = 0.0
        
        # Liquipedia requires proper User-Agent
        self.user_agent = user_agent
        
        if self.game not in self.WIKI_URLS:
            raise ValueError(f"Unsupported game: {game}. Supported: {list(self.WIKI_URLS.keys())}")
        
        self.base_url = self.WIKI_URLS[self.game]

    def _client_instance(self) -> httpx.Client:
        """Get or create HTTP client instance."""
        if self._client is None:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "application/json"
            }
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client

    def _rate_limit(self):
        """Enforce rate limiting (max 1 request per 2 seconds)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        self._last_request_time = time.time()

    def parse_page(self, page_title: str) -> Dict[str, Any]:
        """Parse a Liquipedia page using the MediaWiki API.

        Args:
            page_title: The title of the page to parse

        Returns:
            Parsed page data
        """
        self._rate_limit()
        
        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text|sections|categories"
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise

    def query_category(self, category: str, limit: int = 50) -> List[str]:
        """Query pages in a specific category.

        Args:
            category: Category name (e.g., "Tournaments", "Matches")
            limit: Maximum number of pages to return

        Returns:
            List of page titles in the category
        """
        self._rate_limit()
        
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": limit,
            "format": "json"
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                members = data.get("query", {}).get("categorymembers", [])
                return [member["title"] for member in members]
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise

    def search_pages(self, search_term: str, limit: int = 10) -> List[str]:
        """Search for pages matching a term.

        Args:
            search_term: Search query
            limit: Maximum number of results

        Returns:
            List of matching page titles
        """
        self._rate_limit()
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "srlimit": limit,
            "format": "json"
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                results = data.get("query", {}).get("search", [])
                return [result["title"] for result in results]
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise

    def get_recent_changes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent changes to tournament/match pages.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of recent changes
        """
        self._rate_limit()
        
        params = {
            "action": "query",
            "list": "recentchanges",
            "rcprop": "title|timestamp|ids",
            "rclimit": limit,
            "rcnamespace": 0,  # Main namespace
            "format": "json"
        }
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                return data.get("query", {}).get("recentchanges", [])
            except Exception as exc:
                if attempt < self.max_retries:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise

    def get_matches(self, game: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent tournament pages as match proxies.

        Note: This is a simplified implementation. Full match extraction would
        require parsing tournament bracket pages and extracting match results.

        Args:
            game: Override game (uses instance game if not provided)
            limit: Maximum number of matches to return

        Returns:
            List of normalized match dictionaries
        """
        # Search for recent tournaments
        try:
            # Look for recent tournament/match pages
            recent_pages = self.query_category("Tournaments", limit=limit)
            
            normalized: List[Dict[str, Any]] = []
            
            for page_title in recent_pages[:limit]:
                # Basic match info from page title
                # Full implementation would parse the page content
                
                # Map game names
                game_name_map = {
                    "dota2": "Dota 2",
                    "lol": "League of Legends",
                    "csgo": "Counter-Strike: GO",
                    "valorant": "Valorant",
                    "overwatch": "Overwatch"
                }
                
                normalized.append({
                    "id": page_title.replace(" ", "_"),
                    "title": page_title,
                    "scheduled_time": None,
                    "status": "upcoming",  # Would need to parse page to determine
                    "teams": [],  # Would need to parse bracket data
                    "video_game": game_name_map.get(self.game, self.game.title()),
                    "game": game_name_map.get(self.game, self.game.title()),
                    "provider": "Liquipedia",
                    "source": "liquipedia",
                    "page_url": f"https://liquipedia.net/{self.game}/{page_title.replace(' ', '_')}"
                })
            
            return normalized
        except Exception:
            # Return empty list if fetch fails
            return []

    def close(self):
        """Close the HTTP client connection."""
        if self._client:
            self._client.close()
            self._client = None

    def __del__(self):
        """Cleanup HTTP client on deletion."""
        self.close()
