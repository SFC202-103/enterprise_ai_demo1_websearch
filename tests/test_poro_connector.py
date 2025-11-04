"""
Unit tests for the Poro (Leaguepedia) connector module.

Tests the Poro connector's async methods for fetching League of Legends
esports data from Leaguepedia's Cargo API.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_cargo_teams_response():
    """Mock Cargo API response for teams query."""
    return {
        'cargoquery': [
            {
                'title': {
                    'Name': 'G2 Esports',
                    'Region': 'LEC',
                    'Location': 'Germany',
                    'TeamLocation': 'Berlin',
                    'IsDisbanded': '0',
                    'Short': 'G2',
                    'IsLowercase': '0'
                }
            },
            {
                'title': {
                    'Name': 'Fnatic',
                    'Region': 'LEC',
                    'Location': 'United Kingdom',
                    'TeamLocation': 'London',
                    'IsDisbanded': '0',
                    'Short': 'FNC',
                    'IsLowercase': '0'
                }
            }
        ]
    }


@pytest.fixture
def mock_cargo_tournaments_response():
    """Mock Cargo API response for tournaments query."""
    return {
        'cargoquery': [
            {
                'title': {
                    'Name': 'LEC 2024 Spring',
                    'DateStart': '2024-01-15',
                    'Date': '2024-01-15',
                    'Region': 'LEC',
                    'League': 'LEC',
                    'PrizePoolUSD': '100000',
                    'IsQualifier': '0',
                    'IsPlayoffs': '0'
                }
            }
        ]
    }


@pytest.fixture
def mock_cargo_matches_response():
    """Mock Cargo API response for matches query."""
    return {
        'cargoquery': [
            {
                'title': {
                    'Tournament': 'LEC 2024 Spring',
                    'Team1': 'G2 Esports',
                    'Team2': 'Fnatic',
                    'Winner': '1',
                    'DateTime_UTC': '2024-01-20 18:00:00',
                    'Patch': '14.1',
                    'Team1Score': '2',
                    'Team2Score': '1',
                    'MatchHistory': 'https://matchhistory.example.com/123'
                }
            }
        ]
    }


@pytest.fixture
def mock_cargo_players_response():
    """Mock Cargo API response for players query."""
    return {
        'cargoquery': [
            {
                'title': {
                    'Player': 'Caps',
                    'Team': 'G2 Esports',
                    'Role': 'Mid',
                    'Country': 'Denmark',
                    'Name': 'Rasmus Winther',
                    'NativeName': 'Rasmus Winther',
                    'Age': '24',
                    'IsRetired': 'No'
                }
            }
        ]
    }


@pytest.fixture
def mock_cargo_pentakills_response():
    """Mock Cargo API response for pentakills query."""
    return {
        'cargoquery': [
            {
                'title': {
                    'Name': 'Caps',
                    'Team': 'G2 Esports',
                    'Tournament': 'LEC 2024 Spring',
                    'Date': '2024-02-10',
                    'Champion': 'Azir',
                    'Opponent': 'Fnatic'
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_poro_connector_get_teams(mock_cargo_teams_response):
    """Test fetching teams from Poro connector."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    # Mock the aiohttp session
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_teams_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        teams = await conn.get_teams(region='LEC', limit=50)
        
        assert isinstance(teams, list)
        assert len(teams) == 2
        assert teams[0]['name'] == 'G2 Esports'
        assert teams[0]['region'] == 'LEC'
        assert teams[0]['acronym'] == 'G2'
        assert teams[0]['provider'] == 'poro'
        assert teams[1]['name'] == 'Fnatic'


@pytest.mark.asyncio
async def test_poro_connector_get_teams_no_region(mock_cargo_teams_response):
    """Test fetching all teams without region filter."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_teams_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        teams = await conn.get_teams(limit=50)
        
        assert isinstance(teams, list)
        assert len(teams) == 2


@pytest.mark.asyncio
async def test_poro_connector_get_tournaments(mock_cargo_tournaments_response):
    """Test fetching tournaments from Poro connector."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_tournaments_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        tournaments = await conn.get_tournaments(year=2024, region='LEC', limit=50)
        
        assert isinstance(tournaments, list)
        assert len(tournaments) == 1
        assert tournaments[0]['name'] == 'LEC 2024 Spring'
        assert tournaments[0]['region'] == 'LEC'
        assert tournaments[0]['provider'] == 'poro'
        assert tournaments[0]['game'] == 'League of Legends'


@pytest.mark.asyncio
async def test_poro_connector_get_matches(mock_cargo_matches_response):
    """Test fetching matches from Poro connector."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_matches_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        matches = await conn.get_matches(tournament='LEC 2024 Spring', limit=50)
        
        assert isinstance(matches, list)
        assert len(matches) == 1
        assert matches[0]['title'] == 'G2 Esports vs Fnatic'
        assert matches[0]['provider'] == 'poro'
        assert matches[0]['game'] == 'League of Legends'
        assert matches[0]['status'] == 'finished'
        assert len(matches[0]['teams']) == 2
        assert matches[0]['teams'][0]['name'] == 'G2 Esports'
        assert matches[0]['teams'][0]['score'] == 2
        assert matches[0]['teams'][0]['winner'] is True


@pytest.mark.asyncio
async def test_poro_connector_get_players(mock_cargo_players_response):
    """Test fetching players from Poro connector."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_players_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        players = await conn.get_players(team='G2 Esports', role='Mid', limit=50)
        
        assert isinstance(players, list)
        assert len(players) == 1
        assert players[0]['name'] == 'Caps'
        assert players[0]['team'] == 'G2 Esports'
        assert players[0]['role'] == 'Mid'
        assert players[0]['provider'] == 'poro'
        assert players[0]['retired'] is False


@pytest.mark.asyncio
async def test_poro_connector_get_pentakills(mock_cargo_pentakills_response):
    """Test fetching pentakills from Poro connector."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_cargo_pentakills_response)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        pentakills = await conn.get_pentakills(player='Caps', limit=50)
        
        assert isinstance(pentakills, list)
        assert len(pentakills) == 1
        assert pentakills[0]['player'] == 'Caps'
        assert pentakills[0]['champion'] == 'Azir'
        assert pentakills[0]['provider'] == 'poro'


@pytest.mark.asyncio
async def test_poro_connector_rate_limit_retry():
    """Test that connector retries on 429 rate limit."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector(max_retries=2)
    
    with patch.object(conn, '_get_session') as mock_session:
        # First call returns 429, second succeeds
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {'Retry-After': '1'}
        mock_response_429.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_response_429.__aexit__ = AsyncMock(return_value=None)
        
        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.json = AsyncMock(return_value={'cargoquery': []})
        mock_response_200.__aenter__ = AsyncMock(return_value=mock_response_200)
        mock_response_200.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(side_effect=[mock_response_429, mock_response_200])
        mock_session.return_value = mock_session_obj
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            teams = await conn.get_teams(limit=10)
        
        assert isinstance(teams, list)
        assert mock_session_obj.get.call_count == 2


@pytest.mark.asyncio
async def test_poro_connector_error_handling():
    """Test error handling when API returns errors."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector(max_retries=1)
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value='Internal Server Error')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        teams = await conn.get_teams(limit=10)
        
        # Should return empty list on error
        assert teams == []


@pytest.mark.asyncio
async def test_poro_connector_timeout_handling():
    """Test timeout handling."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector(timeout=1.0, max_retries=1)
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(side_effect=asyncio.TimeoutError())
        mock_session.return_value = mock_session_obj
        
        teams = await conn.get_teams(limit=10)
        
        # Should return empty list on timeout after retries
        assert teams == []


@pytest.mark.asyncio
async def test_poro_connector_close_session():
    """Test closing the aiohttp session."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    # Create a session
    session = await conn._get_session()
    assert session is not None
    assert not session.closed
    
    # Close it
    await conn.close()
    assert session.closed


@pytest.mark.asyncio
async def test_get_poro_connector_singleton():
    """Test the singleton pattern for Poro connector."""
    from src.connectors.poro_connector import get_poro_connector
    
    conn1 = await get_poro_connector()
    conn2 = await get_poro_connector()
    
    assert conn1 is conn2  # Should be the same instance


@pytest.mark.asyncio
async def test_poro_connector_cargo_query_with_joins():
    """Test Cargo query with join conditions."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'cargoquery': []})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        result = await conn._cargo_query(
            tables=['Teams', 'Players'],
            fields=['Teams.Name', 'Players.Player'],
            join_on=[{'left': 'Teams.Name', 'right': 'Players.Team'}],
            limit=10
        )
        
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_poro_connector_cargo_query_with_order_by():
    """Test Cargo query with order by."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={'cargoquery': []})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        result = await conn._cargo_query(
            tables=['Teams'],
            order_by=[{'field': 'Teams.Name', 'desc': True}],
            limit=10
        )
        
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_poro_connector_empty_response():
    """Test handling of empty API responses."""
    from src.connectors.poro_connector import PoroConnector
    
    conn = PoroConnector()
    
    with patch.object(conn, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})  # No cargoquery key
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_obj = AsyncMock()
        mock_session_obj.get = MagicMock(return_value=mock_response)
        mock_session.return_value = mock_session_obj
        
        result = await conn._cargo_query(tables=['Teams'], limit=10)
        
        assert result == []
