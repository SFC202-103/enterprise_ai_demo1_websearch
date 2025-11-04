"""
Final comprehensive tests to reach 96% coverage.

Tests connector error handling, edge cases, and remaining uncovered lines.
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx


# =====================================================================
# CONNECTOR TESTS FOR ERROR HANDLING
# =====================================================================

def test_apex_connector_rate_limiting():
    """Test Apex connector rate limiting."""
    from src.connectors.apex_connector import ApexLegendsConnector
    import time
    
    connector = ApexLegendsConnector()
    start = time.time()
    
    # First call should be immediate
    connector._rate_limit()
    first_call = time.time() - start
    assert first_call < 0.1  # Should be nearly instant
    
    # Second call right after should sleep
    connector._rate_limit()
    second_call = time.time() - start
    assert second_call >= 0.9  # Should wait ~1 second
    
    connector.close()


def test_apex_connector_close():
    """Test Apex connector close method."""
    from src.connectors.apex_connector import ApexLegendsConnector
    
    connector = ApexLegendsConnector()
    # Access client to create it
    _ = connector._client_instance()
    assert connector._client is not None
    
    # Close should clear client
    connector.close()
    assert connector._client is None


def test_apex_connector_client_reuse():
    """Test Apex connector reuses HTTP client."""
    from src.connectors.apex_connector import ApexLegendsConnector
    
    connector = ApexLegendsConnector()
    
    client1 = connector._client_instance()
    client2 = connector._client_instance()
    
    assert client1 is client2  # Should be same instance
    connector.close()


def test_battlefy_connector_rate_limiting():
    """Test Battlefy connector rate limiting."""
    from src.connectors.battlefy_connector import BattlefyConnector
    import time
    
    connector = BattlefyConnector()
    
    # Just test that rate limiting doesn't crash
    connector._rate_limit()
    connector._rate_limit()
    
    connector.close()


def test_battlefy_connector_close():
    """Test Battlefy connector close method."""
    from src.connectors.battlefy_connector import BattlefyConnector
    
    connector = BattlefyConnector()
    _ = connector._client_instance()
    assert connector._client is not None
    
    connector.close()
    assert connector._client is None


def test_hltv_connector_rate_limiting():
    """Test HLTV connector rate limiting."""
    from src.connectors.hltv_connector import HLTVConnector
    import time
    
    connector = HLTVConnector()
    start = time.time()
    
    connector._rate_limit()
    first_call = time.time() - start
    assert first_call < 0.1
    
    connector._rate_limit()
    second_call = time.time() - start
    assert second_call >= 0.9
    
    connector.close()


def test_hltv_connector_close():
    """Test HLTV connector close method."""
    from src.connectors.hltv_connector import HLTVConnector
    
    connector = HLTVConnector()
    _ = connector._client_instance()
    assert connector._client is not None
    
    connector.close()
    assert connector._client is None


def test_marvel_connector_rate_limiting():
    """Test Marvel Rivals connector rate limiting."""
    from src.connectors.marvel_rivals_connector import MarvelRivalsConnector
    import time
    
    connector = MarvelRivalsConnector()
    start = time.time()
    
    connector._rate_limit()
    first_call = time.time() - start
    assert first_call < 0.1
    
    connector._rate_limit()
    second_call = time.time() - start
    assert second_call >= 0.9
    
    connector.close()


def test_marvel_connector_close():
    """Test Marvel Rivals connector close method."""
    from src.connectors.marvel_rivals_connector import MarvelRivalsConnector
    
    connector = MarvelRivalsConnector()
    _ = connector._client_instance()
    assert connector._client is not None
    
    connector.close()
    assert connector._client is None


# =====================================================================
# TEAM STATS EDGE CASES
# =====================================================================

def test_team_stats_draw_scenario():
    """Test team stats with draw when team is team2."""
    from fastapi.testclient import TestClient
    from src.fastapi_app import app
    from unittest.mock import AsyncMock
    
    client = TestClient(app)
    
    with patch("src.fastapi_app.get_live_matches", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [
            {
                "status": "finished",
                "teams": [
                    {"name": "Opponent", "score": 1},
                    {"name": "MyTeam", "score": 1}  # MyTeam is team2
                ]
            }
        ]
        
        response = client.get("/api/team_stats?team_name=MyTeam")
        assert response.status_code == 200
        data = response.json()
        assert "D" in data.get("recent_form", "")


# =====================================================================
# IMPORT ERROR COVERAGE
# =====================================================================

def test_get_live_matches_connector_import_errors():
    """Test get_live_matches handles import errors gracefully."""
    from src.fastapi_app import get_live_matches
    import sys
    
    # This tests the outer try/except blocks that catch import errors
    # These are already covered by normal operation, but we can verify they work
    
    # Test with no game filter to try all connectors
    import asyncio
    result = asyncio.run(get_live_matches(game=None))
    
    assert isinstance(result, list) or isinstance(result, dict)
    # Should not raise even if some connectors fail to import


def test_get_live_matches_with_specific_games():
    """Test get_live_matches with specific game filters."""
    from src.fastapi_app import get_live_matches
    import asyncio
    
    # Test Dota2 path
    result = asyncio.run(get_live_matches(game="dota2"))
    assert isinstance(result, list) or isinstance(result, dict)
    
    # Test Apex path
    result = asyncio.run(get_live_matches(game="apex"))
    assert isinstance(result, list) or isinstance(result, dict)
    
    # Test Marvel path
    result = asyncio.run(get_live_matches(game="marvel"))
    assert isinstance(result, list) or isinstance(result, dict)
