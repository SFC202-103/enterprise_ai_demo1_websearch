from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx


class RiotConnector:
    """Enhanced Riot Games API connector with League of Legends endpoints.

    This connector provides access to Riot's official League of Legends API
    including ranked ladder data, summoner information, and match data.
    
    Supports features demonstrated in the Poro library:
    - Ranked league entries (Challenger, Grandmaster, Master, etc.)
    - Summoner profiles by name or PUUID
    - Match history and details
    - Regional routing (NA, EUW, KR, BR, etc.)
    
    Reference: https://developer.riotgames.com/apis
    """

    # Riot API platforms by region
    PLATFORMS = {
        'NA': 'na1.api.riotgames.com',
        'EUW': 'euw1.api.riotgames.com',
        'EUNE': 'eun1.api.riotgames.com',
        'KR': 'kr.api.riotgames.com',
        'BR': 'br1.api.riotgames.com',
        'LAN': 'la1.api.riotgames.com',
        'LAS': 'la2.api.riotgames.com',
        'OCE': 'oc1.api.riotgames.com',
        'TR': 'tr1.api.riotgames.com',
        'RU': 'ru.api.riotgames.com',
        'JP': 'jp1.api.riotgames.com',
    }
    
    # Regional routing for match data
    REGIONS = {
        'AMERICAS': 'americas.api.riotgames.com',
        'ASIA': 'asia.api.riotgames.com',
        'EUROPE': 'europe.api.riotgames.com',
        'SEA': 'sea.api.riotgames.com',
    }

    def __init__(
        self,
        token: Optional[str] = None,
        platform: str = 'NA',
        region: str = 'AMERICAS',
        timeout: float = 10.0,
        max_retries: int = 2
    ):
        """Initialize Riot API connector.
        
        Args:
            token: Riot API key (or use RIOT_API_TOKEN env var)
            platform: Platform for region-specific endpoints (NA, EUW, KR, etc.)
            region: Regional routing for match/account data (AMERICAS, ASIA, EUROPE)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.token = token or os.getenv("RIOT_API_TOKEN")
        self.platform = platform.upper()
        self.region = region.upper()
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.Client] = None
        
        # Set base URLs
        self.platform_url = f"https://{self.PLATFORMS.get(self.platform, self.PLATFORMS['NA'])}"
        self.region_url = f"https://{self.REGIONS.get(self.region, self.REGIONS['AMERICAS'])}"

    def _client_instance(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _headers(self) -> Dict[str, str]:
        return {"X-Riot-Token": self.token} if self.token else {}
    
    def get_league_entries(
        self,
        queue: str = 'RANKED_SOLO_5x5',
        tier: str = 'CHALLENGER',
        division: str = 'I',
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """Get ranked league entries (similar to Poro's RiotClient example).
        
        Equivalent to:
        riot.path('/lol/league-exp/v4/entries/{queue}/{tier}/{division}', {
            queue: Riot.Queue.RANKED_SOLO_5x5,
            tier: Riot.Tier.CHALLENGER,
            division: Riot.Division.I
        }).get({ query: { page: 1 } })
        
        Args:
            queue: Queue type (RANKED_SOLO_5x5, RANKED_FLEX_SR, RANKED_FLEX_TT)
            tier: Tier (CHALLENGER, GRANDMASTER, MASTER, DIAMOND, etc.)
            division: Division (I, II, III, IV) - not applicable for CHALLENGER/GRANDMASTER/MASTER
            page: Page number for pagination
            
        Returns:
            List of league entries with summoner data
        """
        if not self.token:
            raise ValueError("RIOT_API_TOKEN must be set to fetch league entries")
        
        # For Challenger, Grandmaster, Master - use league endpoint
        if tier.upper() in ['CHALLENGER', 'GRANDMASTER', 'MASTER']:
            url = f"{self.platform_url}/lol/league/v4/{tier.lower()}leagues/by-queue/{queue}"
        else:
            url = f"{self.platform_url}/lol/league-exp/v4/entries/{queue}/{tier}/{division}"
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                params = {"page": page}
                resp = client.get(url, headers=self._headers(), params=params)
                
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
                
                # Normalize response
                if isinstance(data, dict) and 'entries' in data:
                    # Challenger/Grandmaster/Master format
                    entries = data['entries']
                else:
                    # Regular league format
                    entries = data if isinstance(data, list) else []
                
                normalized = []
                for entry in entries:
                    normalized.append({
                        'summoner_id': entry.get('summonerId'),
                        'summoner_name': entry.get('summonerName'),
                        'league_points': entry.get('leaguePoints'),
                        'rank': entry.get('rank'),
                        'tier': tier.upper(),
                        'wins': entry.get('wins'),
                        'losses': entry.get('losses'),
                        'veteran': entry.get('veteran', False),
                        'inactive': entry.get('inactive', False),
                        'fresh_blood': entry.get('freshBlood', False),
                        'hot_streak': entry.get('hotStreak', False),
                        'provider': 'riot'
                    })
                
                return normalized
                
            except Exception:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

        return []
    
    def get_summoner_by_name(self, summoner_name: str) -> Dict[str, Any]:
        """Get summoner information by summoner name.
        
        Args:
            summoner_name: Summoner name
            
        Returns:
            Summoner profile data
        """
        if not self.token:
            raise ValueError("RIOT_API_TOKEN must be set to fetch summoner data")
        
        url = f"{self.platform_url}/lol/summoner/v4/summoners/by-name/{summoner_name}"
        
        for attempt in range(self.max_retries + 1):
            try:
                client = self._client_instance()
                resp = client.get(url, headers=self._headers())
                
                if getattr(resp, "status_code", None) == 429:
                    ra = int(resp.headers.get("Retry-After", 0))
                    if ra and attempt < self.max_retries:
                        time.sleep(ra)
                        continue

                resp.raise_for_status()
                data = resp.json()
                
                return {
                    'id': data.get('id'),
                    'account_id': data.get('accountId'),
                    'puuid': data.get('puuid'),
                    'name': data.get('name'),
                    'summoner_level': data.get('summonerLevel'),
                    'profile_icon_id': data.get('profileIconId'),
                    'revision_date': data.get('revisionDate'),
                    'provider': 'riot'
                }
                
            except Exception:
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise

        return {}

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
