# API Audit Results & Implementation Plan

## Executive Summary

**Audit Date:** November 7, 2025  
**Status:** ✅ APIs functional with enhancement opportunities identified  
**Key Finding:** Player and team data accessible; need AI-optimized aggregation endpoints

---

## Current API Status

### ✅ Working Connectors

1. **Poro (Leaguepedia)** - League of Legends esports data
   - ✅ Players API working (5 players fetched)
   - ⚠️ Teams API needs data (0 teams - may be empty filter)
   - ⚠️ Matches API needs data
   - ⚠️ Champion stats needs data
   - **Available fields:** id, name, real_name, native_name, team, role, country, age, retired, provider, game

2. **Database Models** - SQLAlchemy ORM ready
   - ✅ Team model (id, name, short_name, roster_json)
   - ✅ Player model (id, name, gamertag, team_id, role, stats)
   - ✅ Match, Tournament, TrackedState, TrackedSelection models

### ⚠️ Needs Configuration

3. **Riot Games API**
   - Status: Requires `RIOT_API_TOKEN` environment variable
   - Features: Ranked ladder, summoner profiles, regional routing

4. **PandaScore API**
   - Status: Method signature needs updating (`limit` parameter)
   - Features: Multi-game matches, teams, players

---

## Sample AI Questions & Current Solutions

### Question 1: "What are G2 Esports' players and their stats?"

**Current Solution:**
```bash
GET /api/poro/team-roster?team_name=G2%20Esports
GET /api/poro/players?team=G2%20Esports
```

**Response Example:**
```json
{
  "ok": true,
  "provider": "poro",
  "team": {
    "name": "G2 Esports",
    "region": "LEC",
    "roster": [
      {"name": "Caps", "role": "Mid", "country": "Denmark"},
      {"name": "Hans sama", "role": "Bot", "country": "France"}
    ],
    "roster_size": 5
  }
}
```

**Gaps:**
- ❌ No individual player statistics (KDA, CS, damage)
- ❌ No historical performance metrics
- ❌ No champion mastery data

---

### Question 2: "Who are the top Challenger players in Korea?"

**Current Solution:**
```bash
GET /api/riot/league-entries?platform=KR&tier=CHALLENGER&page=1
```

**Status:** ⚠️ Requires RIOT_API_TOKEN

**Expected Response:**
```json
{
  "ok": true,
  "platform": "KR",
  "tier": "CHALLENGER",
  "entries": [
    {
      "summoner_name": "ShowMaker",
      "league_points": 1523,
      "wins": 145,
      "losses": 89
    }
  ]
}
```

---

### Question 3: "What is T1's recent performance in LCK?"

**Current Solution:**
```bash
GET /api/poro/matches?team=T1&limit=10
GET /api/poro/tournament-standings?tournament=LCK%202024
```

**Status:** ⚠️ Returns 0 matches (Leaguepedia data may be incomplete)

**Enhancement Needed:**
- Calculate win rate from match history
- Determine current form (W-L-W-L pattern)
- Show momentum indicator

---

### Question 4: "Compare Faker vs Caps stats"

**Current Solution:**
```bash
GET /api/poro/players?team=T1
GET /api/poro/players?team=G2%20Esports
```

**Current Data Available:**
- Player name, role, team, country, age
- ❌ Missing: KDA, CS/min, damage, champion pool, win rate

**Enhancement Needed:**
- Aggregate match statistics
- Compare head-to-head performance
- Show champion mastery differences

---

## Professional Implementation Plan

### Phase 1: AI-Optimized Endpoints (Priority: HIGH)

#### 1.1 Team Profile Endpoint
```
GET /api/ai/team_profile?team=<name>&game=<game>
```

**Returns:**
- Team basic info (name, region, acronym)
- Complete roster with roles
- Recent match results (last 10)
- Win/loss record
- Current form streak
- Tournament standings
- Historical achievements

**Implementation:**
```python
async def get_ai_team_profile(team: str, game: str = 'lol'):
    # Fetch from multiple sources
    team_info = await poro.get_team_with_roster(team)
    matches = await poro.get_matches(team=team, limit=10)
    
    # Aggregate data
    wins = sum(1 for m in matches if m['winner'] == team)
    losses = len(matches) - wins
    
    return {
        "team": team_info,
        "stats": {
            "wins": wins,
            "losses": losses,
            "win_rate": wins / len(matches) if matches else 0,
            "recent_form": calculate_form(matches),
            "momentum": "rising" if wins > losses else "falling"
        },
        "recent_matches": matches[:5]
    }
```

#### 1.2 Player Profile Endpoint
```
GET /api/ai/player_profile?player=<name>&game=<game>
```

**Returns:**
- Player basic info (name, role, team, country, age)
- Career statistics
- Champion mastery (if available)
- Recent performance
- Team context

**Implementation:**
```python
async def get_ai_player_profile(player: str, game: str = 'lol'):
    # Fetch player data
    players = await poro.get_players(limit=200)
    player_data = next((p for p in players if p['name'].lower() == player.lower()), None)
    
    if not player_data:
        return {"ok": False, "error": f"Player '{player}' not found"}
    
    # Fetch team roster if player has team
    team_data = None
    if player_data.get('team'):
        team_data = await poro.get_team_with_roster(player_data['team'])
    
    return {
        "player": player_data,
        "team_context": team_data,
        "available_stats": ["role", "team", "country", "age"]
    }
```

#### 1.3 Head-to-Head Comparison
```
GET /api/ai/head_to_head?team1=<name>&team2=<name>&game=<game>
```

**Returns:**
- Historical matchups
- Win/loss record between teams
- Recent encounters
- Statistical comparison

---

### Phase 2: Database Population (Priority: MEDIUM)

#### 2.1 Team Sync Script
```python
# sync_teams.py
async def sync_teams_to_database():
    conn = await get_poro_connector()
    
    # Fetch all teams
    teams = await conn.get_teams(limit=500)
    
    # Insert/update database
    with db.SessionLocal() as session:
        for team in teams:
            db_team = db.Team(
                id=team['id'],
                name=team['name'],
                short_name=team['acronym'],
                roster_json=json.dumps(team.get('roster', []))
            )
            session.merge(db_team)
        session.commit()
```

#### 2.2 Player Sync Script
```python
# sync_players.py
async def sync_players_to_database():
    conn = await get_poro_connector()
    
    # Fetch all players
    players = await conn.get_players(limit=1000)
    
    # Insert/update database
    with db.SessionLocal() as session:
        for player in players:
            db_player = db.Player(
                id=player['id'],
                name=player['name'],
                gamertag=player['name'],
                team_id=player.get('team'),
                role=player.get('role'),
                stats=json.dumps(player)  # Store full player data as JSON
            )
            session.merge(db_player)
        session.commit()
```

---

### Phase 3: Enhanced Database Models (Priority: MEDIUM)

#### 3.1 New Tables

**TeamStats Table:**
```python
class TeamStats(Base):
    __tablename__ = "team_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, ForeignKey('teams.id'))
    tournament = Column(String)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_rate = Column(Float)
    last_updated = Column(String)
```

**PlayerStats Table:**
```python
class PlayerStats(Base):
    __tablename__ = "player_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(String, ForeignKey('players.id'))
    kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    kda = Column(Float)
    games_played = Column(Integer, default=0)
    last_updated = Column(String)
```

---

### Phase 4: OpenAI Function Calling (Priority: HIGH)

#### 4.1 Function Definitions

```python
OPENAI_FUNCTIONS = [
    {
        "name": "get_team_roster",
        "description": "Get team roster with players and their roles",
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "The team name (e.g., 'G2 Esports', 'T1')"
                },
                "game": {
                    "type": "string",
                    "enum": ["lol", "csgo", "dota2"],
                    "description": "The game (default: lol)"
                }
            },
            "required": ["team_name"]
        }
    },
    {
        "name": "get_player_profile",
        "description": "Get detailed player information including team, role, and stats",
        "parameters": {
            "type": "object",
            "properties": {
                "player_name": {
                    "type": "string",
                    "description": "The player name (e.g., 'Faker', 'Caps')"
                },
                "game": {
                    "type": "string",
                    "enum": ["lol", "csgo", "dota2"],
                    "description": "The game (default: lol)"
                }
            },
            "required": ["player_name"]
        }
    },
    {
        "name": "get_tournament_standings",
        "description": "Get current standings for a tournament",
        "parameters": {
            "type": "object",
            "properties": {
                "tournament": {
                    "type": "string",
                    "description": "Tournament name (e.g., 'LEC 2024 Spring', 'LCK 2024')"
                }
            },
            "required": ["tournament"]
        }
    }
]
```

#### 4.2 Function Handlers

```python
async def handle_openai_function_call(function_name: str, arguments: dict):
    if function_name == "get_team_roster":
        return await get_ai_team_profile(**arguments)
    elif function_name == "get_player_profile":
        return await get_ai_player_profile(**arguments)
    elif function_name == "get_tournament_standings":
        conn = await get_poro_connector()
        return await conn.get_tournament_standings(**arguments)
    else:
        return {"error": f"Unknown function: {function_name}"}
```

---

## Implementation Priority

### ✅ Can Implement Immediately

1. **AI Team Profile Endpoint** - Uses existing Poro data
2. **AI Player Profile Endpoint** - Uses existing Poro data
3. **Database Sync Scripts** - Team and Player tables ready
4. **OpenAI Function Definitions** - Can integrate with existing endpoints

### ⚠️ Needs Configuration

5. **Riot API Integration** - Requires API key from https://developer.riotgames.com/
6. **PandaScore Integration** - Needs method signature fix

### 🔮 Future Enhancements

7. **Match Statistics Parsing** - Parse detailed stats from match history URLs
8. **Real-time Statistics** - Implement spectator API
9. **Historical Aggregation** - Compute career statistics from all matches

---

## Testing Plan

### Test Cases for AI Queries

1. ✅ "What are G2 Esports' players?"
   - Endpoint: `/api/poro/team-roster?team_name=G2%20Esports`
   - Expected: Team roster with player names and roles

2. ✅ "Who plays mid for T1?"
   - Endpoint: `/api/poro/players?team=T1`
   - Filter: role == "Mid"
   - Expected: Faker's profile

3. ⚠️ "What is G2's win rate?"
   - Endpoint: `/api/poro/matches?team=G2%20Esports&limit=20`
   - Calculate: wins / total_matches
   - Status: Needs match data

4. ⚠️ "Compare Caps vs Faker"
   - Endpoints: `/api/ai/player_profile` for each
   - Status: Needs implementation

---

## Next Steps

1. **Implement `/api/ai/team_profile` endpoint** (1-2 hours)
2. **Implement `/api/ai/player_profile` endpoint** (1-2 hours)
3. **Create database sync script** (1 hour)
4. **Test with AI assistant** (30 minutes)
5. **Document new endpoints in README** (30 minutes)
6. **Set up Riot API token** (optional, 15 minutes)

---

## Files to Create/Modify

### New Files
- `src/ai_endpoints.py` - AI-optimized endpoints
- `scripts/sync_database.py` - Database population script
- `scripts/test_ai_queries.py` - AI query test script

### Modified Files
- `src/fastapi_app.py` - Register new AI endpoints
- `src/db.py` - Add TeamStats and PlayerStats models
- `README.md` - Document new endpoints

---

## Summary

**Current Status:** ✅ Foundational APIs working  
**Player Data:** ✅ Available from Poro connector  
**Team Data:** ✅ Available from Poro connector (roster JOIN works)  
**Database:** ✅ Models ready for population  

**Key Recommendations:**
1. Implement AI-optimized aggregation endpoints
2. Populate database with connector data
3. Configure OpenAI function calling
4. Add Riot API token for enhanced features

**Estimated Time:** 4-6 hours for full implementation
