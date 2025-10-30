"""Tests for new game connectors to improve coverage."""
import pytest
from src.connectors.apex_connector import ApexLegendsConnector
from src.connectors.battlefy_connector import BattlefyConnector
from src.connectors.hltv_connector import HLTVConnector
from src.connectors.marvel_rivals_connector import MarvelRivalsConnector


def test_apex_connector_get_matches():
    """Test ApexLegendsConnector get_matches method."""
    connector = ApexLegendsConnector()
    matches = connector.get_matches()
    
    # Should return list of matches
    assert isinstance(matches, list)
    # Check structure of matches
    if matches:
        assert "id" in matches[0]
        assert "video_game" in matches[0]


def test_battlefy_connector_get_matches():
    """Test BattlefyConnector get_matches method."""
    connector = BattlefyConnector()
    matches = connector.get_matches()
    
    assert isinstance(matches, list)
    if matches:
        assert "id" in matches[0]
        assert "video_game" in matches[0]


def test_hltv_connector_get_matches():
    """Test HLTVConnector get_matches method."""
    connector = HLTVConnector()
    matches = connector.get_matches()
    
    assert isinstance(matches, list)
    if matches:
        assert "id" in matches[0]
        assert "video_game" in matches[0]


def test_marvel_connector_get_matches():
    """Test MarvelRivalsConnector get_matches method."""
    connector = MarvelRivalsConnector()
    matches = connector.get_matches()
    
    assert isinstance(matches, list)
    if matches:
        assert "id" in matches[0]
        assert "video_game" in matches[0]


def test_connector_error_handling():
    """Test connectors handle errors gracefully."""
    # All connectors should return empty list on error, not crash
    connectors = [
        ApexLegendsConnector(),
        BattlefyConnector(),
        HLTVConnector(),
        MarvelRivalsConnector()
    ]
    
    for connector in connectors:
        # Should not raise exception
        try:
            matches = connector.get_matches()
            assert isinstance(matches, list)
        except Exception as e:
            pytest.fail(f"Connector {type(connector).__name__} raised exception: {e}")
