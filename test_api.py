"""Quick test to check PandaScore API response structure."""
import os
from dotenv import load_dotenv
from src.connectors.pandascore_connector import PandaScoreConnector
import json

load_dotenv()

conn = PandaScoreConnector()
matches = conn.get_matches()

print(f"\nTotal matches: {len(matches)}\n")

if matches:
    print("First match sample:")
    print(json.dumps(matches[0], indent=2))
    
    print("\n\nAll unique video_game values:")
    games = set()
    for m in matches:
        game = m.get('video_game') or m.get('game')
        if game:
            games.add(game)
    
    for game in sorted(games):
        count = sum(1 for m in matches if (m.get('video_game') or m.get('game')) == game)
        print(f"  - {game}: {count} matches")
