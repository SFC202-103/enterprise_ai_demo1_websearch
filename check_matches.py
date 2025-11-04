import json

with open('tests/fixtures/matches.json', 'r') as f:
    data = json.load(f)
    matches = data['matches']
    
print(f"Total matches: {len(matches)}\n")
for i, m in enumerate(matches, 1):
    print(f"{i}. {m['title']}")
    print(f"   Status: {m['status']}")
    print(f"   Game: {m.get('game', 'Unknown')}")
    print()
