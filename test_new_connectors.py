"""Test all new connectors to verify they work correctly."""
import json
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("TESTING NEW ESPORTS CONNECTORS")
print("=" * 80)

# Test 1: OpenDota Connector
print("\n1. Testing OpenDota Connector (Dota 2)")
print("-" * 80)
try:
    from src.connectors.opendota_connector import OpenDotaConnector
    
    conn = OpenDotaConnector()
    matches = conn.get_matches(limit=5)
    
    print(f"✓ Successfully fetched {len(matches)} Dota 2 matches")
    if matches:
        print("\nFirst match:")
        print(f"  - Title: {matches[0]['title']}")
        print(f"  - Game: {matches[0]['video_game']}")
        print(f"  - Status: {matches[0]['status']}")
        if matches[0]['teams']:
            print(f"  - Teams: {matches[0]['teams'][0]['name']} vs {matches[0]['teams'][1]['name']}")
            print(f"  - Score: {matches[0]['teams'][0]['score']}-{matches[0]['teams'][1]['score']}")
except Exception as e:
    print(f"✗ OpenDota test failed: {e}")

# Test 2: Riot Esports Connector
print("\n\n2. Testing Riot LoL Esports Connector")
print("-" * 80)
try:
    from src.connectors.riot_esports_connector import RiotEsportsConnector
    
    conn = RiotEsportsConnector()
    matches = conn.get_matches(limit=5)
    
    print(f"✓ Successfully fetched {len(matches)} League of Legends matches")
    if matches:
        print("\nFirst match:")
        print(f"  - Title: {matches[0]['title']}")
        print(f"  - Game: {matches[0]['video_game']}")
        print(f"  - Status: {matches[0]['status']}")
        if matches[0]['teams']:
            print(f"  - Teams: {len(matches[0]['teams'])} teams")
            for team in matches[0]['teams']:
                print(f"    • {team['name']} ({team['acronym']}): {team['score']} wins")
except Exception as e:
    print(f"✗ Riot Esports test failed: {e}")

# Test 3: Liquipedia Connector
print("\n\n3. Testing Liquipedia Connector (CS:GO)")
print("-" * 80)
try:
    from src.connectors.liquipedia_connector import LiquipediaConnector
    
    # Test with CS:GO
    conn = LiquipediaConnector(game="csgo")
    matches = conn.get_matches(limit=5)
    
    print(f"✓ Successfully fetched {len(matches)} CS:GO tournament pages")
    if matches:
        print("\nFirst tournament:")
        print(f"  - Title: {matches[0]['title']}")
        print(f"  - Game: {matches[0]['video_game']}")
        print(f"  - URL: {matches[0]['page_url']}")
except Exception as e:
    print(f"✗ Liquipedia test failed: {e}")

# Test 4: Integration Test - All Sources
print("\n\n4. Testing Multi-Source Integration")
print("-" * 80)
try:
    all_sources = []
    
    # PandaScore
    try:
        from src.connectors.pandascore_connector import PandaScoreConnector
        conn = PandaScoreConnector()
        matches = conn.get_matches()
        all_sources.append(("PandaScore", len(matches)))
    except Exception as e:
        all_sources.append(("PandaScore", f"Error: {e}"))
    
    # OpenDota
    try:
        from src.connectors.opendota_connector import OpenDotaConnector
        conn = OpenDotaConnector()
        matches = conn.get_matches(limit=10)
        all_sources.append(("OpenDota", len(matches)))
    except Exception as e:
        all_sources.append(("OpenDota", f"Error: {e}"))
    
    # Riot Esports
    try:
        from src.connectors.riot_esports_connector import RiotEsportsConnector
        conn = RiotEsportsConnector()
        matches = conn.get_matches(limit=10)
        all_sources.append(("Riot Esports", len(matches)))
    except Exception as e:
        all_sources.append(("Riot Esports", f"Error: {e}"))
    
    print("Match counts from each source:")
    for source, count in all_sources:
        if isinstance(count, int):
            print(f"  ✓ {source}: {count} matches")
        else:
            print(f"  ✗ {source}: {count}")
            
except Exception as e:
    print(f"✗ Integration test failed: {e}")

print("\n" + "=" * 80)
print("TESTING COMPLETE")
print("=" * 80)
