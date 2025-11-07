"""AI-Optimized Endpoints for Esports Data

This module provides aggregated endpoints specifically designed for AI assistants
to answer complex esports questions by combining data from multiple sources.

Features:
- Team profiles with roster, stats, and recent performance
- Player profiles with team context and career information
- Head-to-head team comparisons
- Tournament summaries with standings
"""
import json
from typing import Any, Dict, List, Optional
from datetime import datetime


async def get_ai_team_profile(team: str, game: str = 'lol') -> Dict[str, Any]:
    """Get comprehensive team profile for AI queries.
    
    Aggregates data from multiple sources:
    - Team roster and basic info
    - Recent match history
    - Win/loss statistics
    - Current form and momentum
    
    Args:
        team: Team name (e.g., 'G2 Esports', 'T1')
        game: Game identifier (default: 'lol')
        
    Returns:
        Dictionary with comprehensive team information
        
    Example:
        >>> profile = await get_ai_team_profile('G2 Esports')
        >>> print(profile['roster'])
        [{'name': 'Caps', 'role': 'Mid'}, ...]
    """
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Fetch team roster with JOIN
        team_info = await conn.get_team_with_roster(team_name=team)
        
        if not team_info.get('ok', True) or not team_info.get('name'):
            # Fallback: Try fetching team from teams list
            teams = await conn.get_teams(limit=500)
            team_match = next((t for t in teams if t['name'].lower() == team.lower()), None)
            
            if team_match:
                # Get players for this team
                players = await conn.get_players(team=team_match['name'], limit=20)
                team_info = {
                    'ok': True,
                    'name': team_match['name'],
                    'region': team_match.get('region'),
                    'location': team_match.get('location'),
                    'roster': [
                        {
                            'name': p.get('name'),
                            'role': p.get('role'),
                            'country': p.get('country')
                        }
                        for p in players if p.get('name')
                    ],
                    'roster_size': len(players),
                    'provider': 'poro'
                }
            else:
                return {
                    "ok": False,
                    "error": f"Team '{team}' not found",
                    "suggestion": "Try exact team name like 'G2 Esports' or 'T1'"
                }
        
        # Fetch recent matches
        matches = await conn.get_matches(team=team, limit=10)
        
        # Calculate statistics
        wins = 0
        losses = 0
        recent_form = []
        
        for match in matches:
            team1 = match.get('team1', {}).get('name', '')
            team2 = match.get('team2', {}).get('name', '')
            winner = match.get('winner', '')
            
            if winner:
                if winner == team or (team.lower() in winner.lower()):
                    wins += 1
                    recent_form.append('W')
                elif team.lower() in team1.lower() or team.lower() in team2.lower():
                    losses += 1
                    recent_form.append('L')
        
        total_matches = wins + losses
        win_rate = (wins / total_matches * 100) if total_matches > 0 else 0
        
        # Determine momentum
        if len(recent_form) >= 3:
            recent_3 = recent_form[:3]
            momentum = "rising" if recent_3.count('W') >= 2 else "falling"
        else:
            momentum = "neutral"
        
        await conn.close()
        
        return {
            "ok": True,
            "provider": "ai_aggregated",
            "game": game,
            "team": {
                "name": team_info.get('name'),
                "region": team_info.get('region'),
                "location": team_info.get('location'),
                "roster": team_info.get('roster', []),
                "roster_size": team_info.get('roster_size', 0)
            },
            "statistics": {
                "recent_matches": total_matches,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 2),
                "recent_form": ' - '.join(recent_form[:5]) if recent_form else "No recent data",
                "momentum": momentum
            },
            "recent_matches": matches[:5],
            "data_sources": ["poro_leaguepedia"]
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to fetch team profile: {str(e)}",
            "team": team,
            "game": game
        }


async def get_ai_player_profile(player: str, game: str = 'lol') -> Dict[str, Any]:
    """Get comprehensive player profile for AI queries.
    
    Aggregates player information including:
    - Basic info (name, role, team, country, age)
    - Team context (roster, region)
    - Career status (active/retired)
    
    Args:
        player: Player name or gamertag (e.g., 'Faker', 'Caps')
        game: Game identifier (default: 'lol')
        
    Returns:
        Dictionary with comprehensive player information
        
    Example:
        >>> profile = await get_ai_player_profile('Faker')
        >>> print(profile['player']['role'])
        'Mid'
    """
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Search for player (fetch more to increase chances of finding)
        all_players = await conn.get_players(limit=1000)
        
        # Try exact match first
        player_data = next(
            (p for p in all_players if p['name'].lower() == player.lower()),
            None
        )
        
        # Try partial match if no exact match
        if not player_data:
            player_data = next(
                (p for p in all_players if player.lower() in p['name'].lower()),
                None
            )
        
        if not player_data:
            await conn.close()
            return {
                "ok": False,
                "error": f"Player '{player}' not found",
                "suggestion": "Try full player name or check spelling",
                "sample_players": [p['name'] for p in all_players[:10]]
            }
        
        # Fetch team context if player has a team
        team_context = None
        if player_data.get('team'):
            team_context = await conn.get_team_with_roster(
                team_name=player_data['team']
            )
            
            # If JOIN failed, try basic team info
            if not team_context.get('ok', True):
                teams = await conn.get_teams(limit=500)
                team_match = next(
                    (t for t in teams if t['name'] == player_data['team']),
                    None
                )
                if team_match:
                    team_context = {
                        'ok': True,
                        'name': team_match['name'],
                        'region': team_match.get('region'),
                        'provider': 'poro'
                    }
        
        await conn.close()
        
        return {
            "ok": True,
            "provider": "ai_aggregated",
            "game": game,
            "player": {
                "name": player_data.get('name'),
                "real_name": player_data.get('real_name'),
                "native_name": player_data.get('native_name'),
                "role": player_data.get('role'),
                "team": player_data.get('team'),
                "country": player_data.get('country'),
                "age": player_data.get('age'),
                "retired": player_data.get('retired', False),
                "status": "Retired" if player_data.get('retired') else "Active"
            },
            "team_context": team_context if team_context and team_context.get('ok', True) else None,
            "available_data": {
                "basic_info": True,
                "team_info": bool(player_data.get('team')),
                "match_statistics": False,  # Not yet implemented
                "champion_mastery": False   # Not yet implemented
            },
            "data_sources": ["poro_leaguepedia"]
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to fetch player profile: {str(e)}",
            "player": player,
            "game": game
        }


async def get_ai_head_to_head(
    team1: str,
    team2: str,
    game: str = 'lol',
    limit: int = 10
) -> Dict[str, Any]:
    """Get head-to-head comparison between two teams.
    
    Args:
        team1: First team name
        team2: Second team name
        game: Game identifier (default: 'lol')
        limit: Number of matches to analyze
        
    Returns:
        Dictionary with head-to-head statistics and comparison
    """
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Fetch matches for both teams
        team1_matches = await conn.get_matches(team=team1, limit=limit)
        team2_matches = await conn.get_matches(team=team2, limit=limit)
        
        # Find matches between these teams
        head_to_head_matches = []
        for match in team1_matches:
            t1_name = match.get('team1', {}).get('name', '')
            t2_name = match.get('team2', {}).get('name', '')
            
            if (team1.lower() in t1_name.lower() and team2.lower() in t2_name.lower()) or \
               (team2.lower() in t1_name.lower() and team1.lower() in t2_name.lower()):
                head_to_head_matches.append(match)
        
        # Calculate head-to-head record
        team1_wins = 0
        team2_wins = 0
        
        for match in head_to_head_matches:
            winner = match.get('winner', '').lower()
            if team1.lower() in winner:
                team1_wins += 1
            elif team2.lower() in winner:
                team2_wins += 1
        
        await conn.close()
        
        return {
            "ok": True,
            "provider": "ai_aggregated",
            "game": game,
            "teams": {
                "team1": team1,
                "team2": team2
            },
            "head_to_head": {
                "total_matches": len(head_to_head_matches),
                "team1_wins": team1_wins,
                "team2_wins": team2_wins,
                "most_recent": head_to_head_matches[0] if head_to_head_matches else None
            },
            "recent_matches": head_to_head_matches[:5],
            "data_sources": ["poro_leaguepedia"]
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to fetch head-to-head data: {str(e)}",
            "teams": {"team1": team1, "team2": team2}
        }


async def get_ai_tournament_summary(
    tournament: str,
    limit: int = 20
) -> Dict[str, Any]:
    """Get comprehensive tournament summary.
    
    Args:
        tournament: Tournament name (e.g., 'LEC 2024 Spring')
        limit: Maximum number of teams in standings
        
    Returns:
        Dictionary with tournament information and standings
    """
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Fetch tournament standings
        standings = await conn.get_tournament_standings(
            tournament=tournament,
            limit=limit
        )
        
        # Fetch recent matches from this tournament
        matches = await conn.get_matches(tournament=tournament, limit=20)
        
        await conn.close()
        
        # Calculate tournament statistics
        total_teams = len(standings)
        total_matches = len(matches)
        
        # Identify leaders
        leader = standings[0] if standings else None
        
        return {
            "ok": True,
            "provider": "ai_aggregated",
            "tournament": tournament,
            "statistics": {
                "total_teams": total_teams,
                "total_matches_recorded": total_matches,
                "current_leader": leader.get('team') if leader else None,
                "leader_record": f"{leader.get('wins', 0)}-{leader.get('losses', 0)}" if leader else None
            },
            "standings": standings,
            "recent_matches": matches[:5],
            "data_sources": ["poro_leaguepedia"]
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to fetch tournament summary: {str(e)}",
            "tournament": tournament
        }


# OpenAI Function Definitions for AI Assistant
OPENAI_FUNCTIONS = [
    {
        "name": "get_team_roster",
        "description": "Get detailed team information including roster, players, roles, and recent performance statistics. Use this when users ask about team composition, players, or team information.",
        "parameters": {
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "description": "The team name (e.g., 'G2 Esports', 'T1', 'Team Liquid')"
                },
                "game": {
                    "type": "string",
                    "enum": ["lol", "csgo", "dota2"],
                    "description": "The game (default: lol for League of Legends)",
                    "default": "lol"
                }
            },
            "required": ["team"]
        }
    },
    {
        "name": "get_player_profile",
        "description": "Get detailed player information including role, team, country, age, and career status. Use this when users ask about specific players.",
        "parameters": {
            "type": "object",
            "properties": {
                "player": {
                    "type": "string",
                    "description": "The player name or gamertag (e.g., 'Faker', 'Caps', 'Doublelift')"
                },
                "game": {
                    "type": "string",
                    "enum": ["lol", "csgo", "dota2"],
                    "description": "The game (default: lol for League of Legends)",
                    "default": "lol"
                }
            },
            "required": ["player"]
        }
    },
    {
        "name": "get_head_to_head",
        "description": "Compare two teams with head-to-head statistics and recent matchups. Use this when users ask to compare teams or want to know their historical matchup record.",
        "parameters": {
            "type": "object",
            "properties": {
                "team1": {
                    "type": "string",
                    "description": "First team name"
                },
                "team2": {
                    "type": "string",
                    "description": "Second team name"
                },
                "game": {
                    "type": "string",
                    "enum": ["lol", "csgo", "dota2"],
                    "default": "lol"
                }
            },
            "required": ["team1", "team2"]
        }
    },
    {
        "name": "get_tournament_standings",
        "description": "Get current tournament standings, team records, and win rates. Use this when users ask about tournament rankings or standings.",
        "parameters": {
            "type": "object",
            "properties": {
                "tournament": {
                    "type": "string",
                    "description": "Tournament name (e.g., 'LEC 2024 Spring', 'LCK 2024', 'Worlds 2024')"
                }
            },
            "required": ["tournament"]
        }
    }
]


async def handle_openai_function_call(
    function_name: str,
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Route OpenAI function calls to appropriate handlers.
    
    Args:
        function_name: Name of the function to call
        arguments: Dictionary of function arguments
        
    Returns:
        Function result as dictionary
    """
    if function_name == "get_team_roster":
        return await get_ai_team_profile(**arguments)
    elif function_name == "get_player_profile":
        return await get_ai_player_profile(**arguments)
    elif function_name == "get_head_to_head":
        return await get_ai_head_to_head(**arguments)
    elif function_name == "get_tournament_standings":
        return await get_ai_tournament_summary(**arguments)
    else:
        return {
            "ok": False,
            "error": f"Unknown function: {function_name}",
            "available_functions": [f["name"] for f in OPENAI_FUNCTIONS]
        }
