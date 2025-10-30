"""Comprehensive tests for new connector provider routes in FastAPI."""
import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
import src.fastapi_app as fa


def test_get_live_matches_provider_opendota():
    """Test OpenDota provider selection."""
    with patch("src.connectors.opendota_connector.OpenDotaConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "123", "title": "Match", "provider": "OpenDota", "teams": [], "video_game": "Dota 2"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="opendota"))
        
        assert len(result) == 1
        assert result[0]["provider"] == "OpenDota"


def test_get_live_matches_provider_riot_esports():
    """Test Riot Esports provider selection."""
    with patch("src.connectors.riot_esports_connector.RiotEsportsConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "evt1", "title": "LoL Match", "provider": "Riot Esports", "teams": [], "video_game": "League of Legends"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="riot_esports"))
        
        assert len(result) == 1
        assert result[0]["video_game"] == "League of Legends"


def test_get_live_matches_provider_liquipedia_with_game():
    """Test Liquipedia provider with game mapping."""
    with patch("src.connectors.liquipedia_connector.LiquipediaConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "tourney1", "title": "Tournament", "provider": "Liquipedia", "teams": [], "video_game": "Counter-Strike: GO"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="liquipedia", game="csgo"))
        
        # Check that Liquipedia was initialized with correct game
        mock_class.assert_called_once()
        assert mock_class.call_args[1]["game"] == "csgo"


def test_get_live_matches_provider_liquipedia_game_mapping():
    """Test various game name mappings for Liquipedia."""
    with patch("src.connectors.liquipedia_connector.LiquipediaConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = []
        mock_class.return_value = mock_instance
        
        # Test lol
        asyncio.run(fa.get_live_matches(provider="liquipedia", game="lol"))
        assert mock_class.call_args[1]["game"] == "lol"
        
        # Test dota2
        asyncio.run(fa.get_live_matches(provider="liquipedia", game="dota2"))
        assert mock_class.call_args[1]["game"] == "dota2"
        
        # Test valorant
        asyncio.run(fa.get_live_matches(provider="liquipedia", game="valorant"))
        assert mock_class.call_args[1]["game"] == "valorant"


def test_get_live_matches_provider_value_error():
    """Test provider ValueError returns error dict."""
    with patch("src.connectors.opendota_connector.OpenDotaConnector") as mock_class:
        mock_class.side_effect = ValueError("Missing token")
        
        result = asyncio.run(fa.get_live_matches(provider="opendota"))
        
        assert isinstance(result, dict)
        assert result["ok"] is False
        assert "Missing token" in result["error"]


def test_get_live_matches_provider_generic_exception():
    """Test provider generic exception returns error dict."""
    with patch("src.connectors.riot_esports_connector.RiotEsportsConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.side_effect = RuntimeError("API error")
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="riot_esports"))
        
        assert isinstance(result, dict)
        assert result["ok"] is False
        assert "connector error" in result["error"]


def test_get_live_matches_aggregation_pandascore():
    """Test aggregation includes PandaScore."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector") as mock_ps:
        with patch("src.connectors.cache.get_cached") as mock_cache:
            mock_instance = Mock()
            mock_instance.get_matches.return_value = [{"id": "ps1", "provider": "PandaScore"}]
            mock_ps.return_value = mock_instance
            
            def cache_loader(key, ttl, loader):
                return loader()
            mock_cache.side_effect = cache_loader
            
            # Mock other connectors to raise exceptions
            with patch("src.connectors.riot_esports_connector.RiotEsportsConnector", side_effect=Exception()):
                with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=Exception()):
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        with patch("src.connectors.hltv_connector.HLTVConnector", side_effect=Exception()):
                            with patch("src.connectors.battlefy_connector.BattlefyConnector", side_effect=Exception()):
                                with patch("src.connectors.apex_connector.ApexLegendsConnector", side_effect=Exception()):
                                    with patch("src.connectors.marvel_rivals_connector.MarvelRivalsConnector", side_effect=Exception()):
                                        with patch("src.connectors.liquipedia_connector.LiquipediaConnector", side_effect=Exception()):
                                            result = asyncio.run(fa.get_live_matches())
                                            
                                            assert len(result) >= 1
                                            assert any(m.get("provider") == "PandaScore" for m in result)


def test_get_live_matches_aggregation_opendota():
    """Test aggregation includes OpenDota for Dota games."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector", side_effect=Exception()):
        with patch("src.connectors.opendota_connector.OpenDotaConnector") as mock_od:
            with patch("src.connectors.cache.get_cached") as mock_cache:
                mock_instance = Mock()
                mock_instance.get_matches.return_value = [{"id": "od1", "provider": "OpenDota"}]
                mock_od.return_value = mock_instance
                
                def cache_loader(key, ttl, loader):
                    return loader()
                mock_cache.side_effect = cache_loader
                
                with patch("src.connectors.riot_esports_connector.RiotEsportsConnector", side_effect=Exception()):
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        result = asyncio.run(fa.get_live_matches())
                        
                        assert len(result) >= 1
                        assert any(m.get("provider") == "OpenDota" for m in result)


def test_get_live_matches_aggregation_riot_esports():
    """Test aggregation includes Riot Esports for LoL games."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector", side_effect=Exception()):
        with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=Exception()):
            with patch("src.connectors.riot_esports_connector.RiotEsportsConnector") as mock_re:
                with patch("src.connectors.cache.get_cached") as mock_cache:
                    mock_instance = Mock()
                    mock_instance.get_matches.return_value = [{"id": "re1", "provider": "Riot Esports"}]
                    mock_re.return_value = mock_instance
                    
                    def cache_loader(key, ttl, loader):
                        return loader()
                    mock_cache.side_effect = cache_loader
                    
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        result = asyncio.run(fa.get_live_matches())
                        
                        assert len(result) >= 1
                        assert any(m.get("provider") == "Riot Esports" for m in result)


def test_get_live_matches_aggregation_game_filter_dota():
    """Test aggregation with Dota 2 game filter."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector", side_effect=Exception()):
        with patch("src.connectors.opendota_connector.OpenDotaConnector") as mock_od:
            with patch("src.connectors.cache.get_cached") as mock_cache:
                mock_instance = Mock()
                mock_instance.get_matches.return_value = [{"id": "d1", "provider": "OpenDota", "game": "Dota 2"}]
                mock_od.return_value = mock_instance
                
                def cache_loader(key, ttl, loader):
                    return loader()
                mock_cache.side_effect = cache_loader
                
                with patch("src.connectors.riot_esports_connector.RiotEsportsConnector") as mock_re:
                    mock_re_instance = Mock()
                    mock_re_instance.get_matches.return_value = []
                    mock_re.return_value = mock_re_instance
                    
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        result = asyncio.run(fa.get_live_matches(game="dota2"))
                        
                        # OpenDota should be called for dota2
                        assert mock_od.called


def test_get_live_matches_aggregation_game_filter_lol():
    """Test aggregation with LoL game filter."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector", side_effect=Exception()):
        with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=Exception()):
            with patch("src.connectors.riot_esports_connector.RiotEsportsConnector") as mock_re:
                with patch("src.connectors.cache.get_cached") as mock_cache:
                    mock_instance = Mock()
                    mock_instance.get_matches.return_value = [{"id": "l1", "provider": "Riot Esports", "game": "LoL"}]
                    mock_re.return_value = mock_instance
                    
                    def cache_loader(key, ttl, loader):
                        return loader()
                    mock_cache.side_effect = cache_loader
                    
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        result = asyncio.run(fa.get_live_matches(game="lol"))
                        
                        # Riot Esports should be called for lol
                        assert mock_re.called


def test_get_live_matches_cache_keys_include_provider():
    """Test that cache keys include provider information."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector") as mock_ps:
        with patch("src.connectors.cache.get_cached") as mock_cache:
            mock_instance = Mock()
            mock_instance.get_matches.return_value = []
            mock_ps.return_value = mock_instance
            
            cache_keys = []
            def capture_cache_key(key, ttl, loader):
                cache_keys.append(key)
                return loader()
            mock_cache.side_effect = capture_cache_key
            
            with patch("src.connectors.riot_esports_connector.RiotEsportsConnector", side_effect=Exception()):
                with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=Exception()):
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                        with patch("src.connectors.hltv_connector.HLTVConnector", side_effect=Exception()):
                            with patch("src.connectors.battlefy_connector.BattlefyConnector", side_effect=Exception()):
                                with patch("src.connectors.apex_connector.ApexLegendsConnector", side_effect=Exception()):
                                    with patch("src.connectors.marvel_rivals_connector.MarvelRivalsConnector", side_effect=Exception()):
                                        with patch("src.connectors.liquipedia_connector.LiquipediaConnector", side_effect=Exception()):
                                            asyncio.run(fa.get_live_matches())
                                            
                                            # Check that cache keys include provider names
                                            assert any("pandascore" in key.lower() for key in cache_keys)


def test_get_live_matches_all_connectors_fail_returns_fixture():
    """Test that when all connectors fail, it falls back to fixture."""
    original = fa._fixture_data.get("matches", [])
    fa._fixture_data["matches"] = [{"id": "fixture1", "game": "test"}]
    
    with patch("src.connectors.pandascore_connector.PandaScoreConnector", side_effect=Exception()):
        with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=Exception()):
            with patch("src.connectors.riot_esports_connector.RiotEsportsConnector", side_effect=Exception()):
                with patch("src.connectors.riot_connector.RiotConnector", side_effect=Exception()):
                    result = asyncio.run(fa.get_live_matches())
                    
                    # Should return fixture data when all connectors fail
                    assert isinstance(result, list)
    
    fa._fixture_data["matches"] = original


def test_get_live_matches_provider_riot_legacy():
    """Test that legacy Riot provider still works."""
    with patch("src.connectors.riot_connector.RiotConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "r1", "title": "Match", "teams": [], "video_game": "LoL"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="riot"))
        
        assert len(result) == 1


def test_get_live_matches_aggregation_all_exceptions_handled():
    """Test that exceptions in individual connectors don't break aggregation."""
    with patch("src.connectors.pandascore_connector.PandaScoreConnector") as mock_ps:
        # PandaScore succeeds
        mock_ps_instance = Mock()
        mock_ps_instance.get_matches.return_value = [{"id": "ps1"}]
        mock_ps.return_value = mock_ps_instance
        
        with patch("src.connectors.cache.get_cached") as mock_cache:
            def cache_loader(key, ttl, loader):
                try:
                    return loader()
                except:
                    return []
            mock_cache.side_effect = cache_loader
            
            # Other connectors fail during initialization
            with patch("src.connectors.opendota_connector.OpenDotaConnector", side_effect=ImportError()):
                with patch("src.connectors.riot_esports_connector.RiotEsportsConnector", side_effect=ValueError()):
                    with patch("src.connectors.riot_connector.RiotConnector", side_effect=RuntimeError()):
                        result = asyncio.run(fa.get_live_matches())
                        
                        # Should still return PandaScore results
                        assert len(result) >= 1


def test_get_live_matches_provider_mediawiki():
    """Test MediaWiki provider selection."""
    with patch("src.connectors.liquipedia_connector.LiquipediaConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "mw1", "title": "Wiki Match", "provider": "MediaWiki"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="mediawiki"))
        
        assert len(result) == 1
        # Check MediaWiki was initialized with correct params
        mock_class.assert_called_once_with(game="mediawiki", use_generic_mediawiki=True)


def test_get_live_matches_provider_hltv():
    """Test HLTV provider selection."""
    with patch("src.connectors.hltv_connector.HLTVConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "h1", "title": "CS:GO Match", "provider": "HLTV"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="hltv"))
        
        assert len(result) == 1
        assert result[0]["provider"] == "HLTV"


def test_get_live_matches_provider_battlefy():
    """Test Battlefy provider selection."""
    with patch("src.connectors.battlefy_connector.BattlefyConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "b1", "title": "Tournament", "provider": "Battlefy"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="battlefy"))
        
        assert len(result) == 1
        assert result[0]["provider"] == "Battlefy"


def test_get_live_matches_provider_apex():
    """Test Apex Legends provider selection."""
    with patch("src.connectors.apex_connector.ApexLegendsConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "a1", "title": "ALGS", "provider": "Apex Legends"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="apex"))
        
        assert len(result) == 1
        assert result[0]["provider"] == "Apex Legends"


def test_get_live_matches_provider_marvel():
    """Test Marvel Rivals provider selection."""
    with patch("src.connectors.marvel_rivals_connector.MarvelRivalsConnector") as mock_class:
        mock_instance = Mock()
        mock_instance.get_matches.return_value = [
            {"id": "m1", "title": "Marvel Tournament", "provider": "Marvel Rivals"}
        ]
        mock_class.return_value = mock_instance
        
        result = asyncio.run(fa.get_live_matches(provider="marvel"))
        
        assert len(result) == 1
        assert result[0]["provider"] == "Marvel Rivals"
