"""Poro API connector for Leaguepedia data.

This connector integrates with the Leaguepedia (Cargo) API through the Poro
library pattern. It provides access to League of Legends esports data including
teams, tournaments, players, matches, and statistics.

The connector follows the same pattern as other connectors in this project:
- Async/await for all network operations
- Environment-based configuration
- Proper error handling and retries
- Data normalization to common format

Reference: https://github.com/pacexy/poro
API Docs: https://lol.fandom.com/wiki/Special:CargoQuery
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp


class PoroConnector:
    """Connector for Leaguepedia Cargo API.
    
    This connector queries the Leaguepedia wiki's Cargo database which contains
    comprehensive League of Legends esports data. No API key is required as it's
    a public wiki API.
    
    Features:
    - Teams and rosters
    - Tournament information
    - Match history and results
    - Player statistics
    - Historical pentakills and achievements
    
    Example usage:
        connector = PoroConnector()
        teams = await connector.get_teams(region="LEC")
        matches = await connector.get_matches(tournament="LEC 2024 Spring")
    """

    BASE_URL = "https://lol.fandom.com/api.php"
    
    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        """Initialize the Poro connector.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    'User-Agent': 'EsportsAI/1.0 (Educational Demo)',
                }
            )
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _cargo_query(
        self,
        tables: List[str],
        fields: Optional[List[str]] = None,
        where: Optional[str] = None,
        join_on: Optional[List[Dict[str, str]]] = None,
        group_by: Optional[List[str]] = None,
        order_by: Optional[List[Dict[str, Any]]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute a Cargo query against Leaguepedia.
        
        This method constructs and executes a Cargo API query similar to how
        the Poro library's CargoClient.query() works.
        
        Args:
            tables: List of table names to query
            fields: List of fields to return (defaults to all fields)
            where: SQL WHERE clause
            join_on: List of join conditions {left: field, right: field}
            group_by: List of fields to group by
            order_by: List of order specifications {field: name, desc: bool}
            limit: Maximum results to return
            offset: Number of results to skip
            
        Returns:
            List of result dictionaries
        """
        session = await self._get_session()
        
        # Build Cargo query parameters
        params = {
            'action': 'cargoquery',
            'format': 'json',
            'tables': ','.join(tables),
            'limit': min(limit, 500),  # Cargo max is 500
            'offset': offset,
        }
        
        if fields:
            params['fields'] = ','.join(fields)
        
        if where:
            params['where'] = where
        
        if join_on:
            join_clauses = []
            for join in join_on:
                join_clauses.append(f"{join['left']}={join['right']}")
            params['join_on'] = ','.join(join_clauses)
        
        if group_by:
            params['group_by'] = ','.join(group_by)
        
        if order_by:
            order_clauses = []
            for order in order_by:
                field = order['field']
                desc = ' DESC' if order.get('desc', False) else ''
                order_clauses.append(f"{field}{desc}")
            params['order_by'] = ','.join(order_clauses)
        
        # Retry logic
        for attempt in range(self.max_retries + 1):
            try:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status == 429:
                        # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 5))
                        if attempt < self.max_retries:
                            await asyncio.sleep(retry_after)
                            continue
                        raise Exception(f"Rate limited after {self.max_retries} retries")
                    
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"HTTP {response.status}: {text}")
                    
                    data = await response.json()
                    
                    # Extract results from Cargo response format
                    if 'cargoquery' in data:
                        return [item['title'] for item in data['cargoquery']]
                    
                    return []
                    
            except asyncio.TimeoutError:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise Exception(f"Request timeout after {self.max_retries} retries")
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
    
    async def get_teams(
        self,
        region: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get League of Legends teams.
        
        Args:
            region: Filter by region (e.g., 'LEC', 'LCS', 'LCK', 'LPL')
            limit: Maximum number of teams to return
            
        Returns:
            List of team dictionaries with normalized structure
        """
        fields = [
            'Teams.Name',
            'Teams.Region',
            'Teams.Location',
            'Teams.TeamLocation',
            'Teams.IsDisbanded',
            'Teams.Short',
            'Teams.IsLowercase'
        ]
        
        where = None
        if region:
            where = f'Teams.Region = "{region}"'
        
        try:
            results = await self._cargo_query(
                tables=['Teams'],
                fields=fields,
                where=where,
                limit=limit,
                order_by=[{'field': 'Teams.Name', 'desc': False}]
            )
            
            # Normalize to common format
            normalized = []
            for team in results:
                normalized.append({
                    'id': f"poro_team_{team.get('Name', '').replace(' ', '_').lower()}",
                    'name': team.get('Name', 'Unknown Team'),
                    'acronym': team.get('Short', team.get('Name', '')[:3].upper()),
                    'region': team.get('Region'),
                    'location': team.get('Location') or team.get('TeamLocation'),
                    'active': team.get('IsDisbanded') != '1',
                    'provider': 'poro',
                    'image_url': None  # Leaguepedia doesn't provide direct image URLs
                })
            
            return normalized
        except Exception as e:
            print(f"Error fetching teams from Poro: {e}")
            return []
    
    async def get_tournaments(
        self,
        year: Optional[int] = None,
        region: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get League of Legends tournaments.
        
        Args:
            year: Filter by year
            region: Filter by region
            limit: Maximum number of tournaments to return
            
        Returns:
            List of tournament dictionaries
        """
        fields = [
            'Tournaments.Name',
            'Tournaments.DateStart',
            'Tournaments.Date',
            'Tournaments.Region',
            'Tournaments.League',
            'Tournaments.PrizePoolUSD',
            'Tournaments.IsQualifier',
            'Tournaments.IsPlayoffs'
        ]
        
        where_clauses = []
        if year:
            where_clauses.append(f'Tournaments.Year = {year}')
        if region:
            where_clauses.append(f'Tournaments.Region = "{region}"')
        
        where = ' AND '.join(where_clauses) if where_clauses else None
        
        try:
            results = await self._cargo_query(
                tables=['Tournaments'],
                fields=fields,
                where=where,
                limit=limit,
                order_by=[{'field': 'Tournaments.DateStart', 'desc': True}]
            )
            
            # Normalize to common format
            normalized = []
            for tournament in results:
                normalized.append({
                    'id': f"poro_tournament_{tournament.get('Name', '').replace(' ', '_').lower()}",
                    'name': tournament.get('Name', 'Unknown Tournament'),
                    'start_date': tournament.get('DateStart') or tournament.get('Date'),
                    'region': tournament.get('Region'),
                    'league': tournament.get('League'),
                    'prize_pool_usd': tournament.get('PrizePoolUSD'),
                    'is_qualifier': tournament.get('IsQualifier') == '1',
                    'is_playoffs': tournament.get('IsPlayoffs') == '1',
                    'provider': 'poro',
                    'game': 'League of Legends'
                })
            
            return normalized
        except Exception as e:
            print(f"Error fetching tournaments from Poro: {e}")
            return []
    
    async def get_matches(
        self,
        tournament: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get League of Legends match results.
        
        Args:
            tournament: Filter by tournament name
            team: Filter by team name
            limit: Maximum number of matches to return
            
        Returns:
            List of match dictionaries normalized to common format
        """
        fields = [
            'ScoreboardGames.Tournament',
            'ScoreboardGames.Team1',
            'ScoreboardGames.Team2',
            'ScoreboardGames.Winner',
            'ScoreboardGames.DateTime_UTC',
            'ScoreboardGames.Patch',
            'ScoreboardGames.Team1Score',
            'ScoreboardGames.Team2Score',
            'ScoreboardGames.MatchHistory'
        ]
        
        where_clauses = []
        if tournament:
            where_clauses.append(f'ScoreboardGames.Tournament = "{tournament}"')
        if team:
            where_clauses.append(f'(ScoreboardGames.Team1 = "{team}" OR ScoreboardGames.Team2 = "{team}")')
        
        where = ' AND '.join(where_clauses) if where_clauses else None
        
        try:
            results = await self._cargo_query(
                tables=['ScoreboardGames'],
                fields=fields,
                where=where,
                limit=limit,
                order_by=[{'field': 'ScoreboardGames.DateTime_UTC', 'desc': True}]
            )
            
            # Normalize to common format
            normalized = []
            for match in results:
                team1_name = match.get('Team1', 'Team 1')
                team2_name = match.get('Team2', 'Team 2')
                winner = match.get('Winner', '')
                
                normalized.append({
                    'id': f"poro_match_{match.get('Tournament', '')}_{team1_name}_{team2_name}".replace(' ', '_').lower(),
                    'title': f"{team1_name} vs {team2_name}",
                    'tournament': {
                        'name': match.get('Tournament', 'Unknown Tournament')
                    },
                    'teams': [
                        {
                            'name': team1_name,
                            'score': int(match.get('Team1Score', 0)) if match.get('Team1Score') else 0,
                            'winner': winner == '1'
                        },
                        {
                            'name': team2_name,
                            'score': int(match.get('Team2Score', 0)) if match.get('Team2Score') else 0,
                            'winner': winner == '2'
                        }
                    ],
                    'scheduled_at': match.get('DateTime_UTC'),
                    'status': 'finished',
                    'game': 'League of Legends',
                    'patch': match.get('Patch'),
                    'match_history_url': match.get('MatchHistory'),
                    'provider': 'poro'
                })
            
            return normalized
        except Exception as e:
            print(f"Error fetching matches from Poro: {e}")
            return []
    
    async def get_players(
        self,
        team: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get League of Legends players.
        
        Args:
            team: Filter by current team
            role: Filter by role (Top, Jungle, Mid, Bot, Support)
            limit: Maximum number of players to return
            
        Returns:
            List of player dictionaries
        """
        fields = [
            'Players.Player',
            'Players.Team',
            'Players.Role',
            'Players.Country',
            'Players.Name',
            'Players.NativeName',
            'Players.Age',
            'Players.IsRetired'
        ]
        
        where_clauses = []
        if team:
            where_clauses.append(f'Players.Team = "{team}"')
        if role:
            where_clauses.append(f'Players.Role = "{role}"')
        
        where = ' AND '.join(where_clauses) if where_clauses else None
        
        try:
            results = await self._cargo_query(
                tables=['Players'],
                fields=fields,
                where=where,
                limit=limit,
                order_by=[{'field': 'Players.Player', 'desc': False}]
            )
            
            # Normalize to common format
            normalized = []
            for player in results:
                normalized.append({
                    'id': f"poro_player_{player.get('Player', '').lower()}",
                    'name': player.get('Player', 'Unknown Player'),
                    'real_name': player.get('Name'),
                    'native_name': player.get('NativeName'),
                    'team': player.get('Team'),
                    'role': player.get('Role'),
                    'country': player.get('Country'),
                    'age': player.get('Age'),
                    'retired': player.get('IsRetired') == 'Yes',
                    'provider': 'poro',
                    'game': 'League of Legends'
                })
            
            return normalized
        except Exception as e:
            print(f"Error fetching players from Poro: {e}")
            return []
    
    async def get_pentakills(self, player: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pentakill achievements.
        
        Args:
            player: Filter by player name
            limit: Maximum number of pentakills to return
            
        Returns:
            List of pentakill records
        """
        fields = [
            'Pentakills.Name',
            'Pentakills.Team',
            'Pentakills.Tournament',
            'Pentakills.Date',
            'Pentakills.Champion',
            'Pentakills.Opponent'
        ]
        
        where = f'Pentakills.Name = "{player}"' if player else None
        
        try:
            results = await self._cargo_query(
                tables=['Pentakills'],
                fields=fields,
                where=where,
                limit=limit,
                order_by=[{'field': 'Pentakills.Date', 'desc': True}]
            )
            
            normalized = []
            for penta in results:
                normalized.append({
                    'player': penta.get('Name'),
                    'team': penta.get('Team'),
                    'tournament': penta.get('Tournament'),
                    'date': penta.get('Date'),
                    'champion': penta.get('Champion'),
                    'opponent': penta.get('Opponent'),
                    'provider': 'poro'
                })
            
            return normalized
        except Exception as e:
            print(f"Error fetching pentakills from Poro: {e}")
            return []


# Singleton instance for reuse
_poro_connector_instance: Optional[PoroConnector] = None


async def get_poro_connector() -> PoroConnector:
    """Get or create the singleton Poro connector instance."""
    global _poro_connector_instance
    if _poro_connector_instance is None:
        _poro_connector_instance = PoroConnector()
    return _poro_connector_instance
