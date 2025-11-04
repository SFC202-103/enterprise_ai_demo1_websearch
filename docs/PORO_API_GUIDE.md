# Poro API Integration Guide

## Overview

This guide demonstrates how our Python-based Poro connector provides the same functionality as the original TypeScript `poro` npm package. All examples show both the TypeScript original and our Python equivalent.

---

## Table of Contents

1. [Leaguepedia Cargo Queries](#leaguepedia-cargo-queries)
2. [Riot Games API Integration](#riot-games-api-integration)
3. [Advanced Query Patterns](#advanced-query-patterns)
4. [API Endpoints](#api-endpoints)
5. [Usage Examples](#usage-examples)

---

## Leaguepedia Cargo Queries

### Basic Team Query

**TypeScript (Original Poro):**
```typescript
import { CargoClient } from 'poro'

const cargo = new CargoClient()
const teams = await cargo.query({
  tables: ['Teams'],
  fields: ['Teams.Name', 'Teams.Region'],
})
```

**Python (Our Implementation):**
```python
from src.connectors.poro_connector import get_poro_connector

conn = await get_poro_connector()
teams = await conn.get_teams(limit=50)
# Returns: [{'name': 'G2 Esports', 'region': 'LEC', ...}, ...]
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/teams?limit=50
```

---

### Filtered Query (WHERE Clause)

**TypeScript (Original Poro):**
```typescript
const g2 = await cargo.query({
  tables: ['Teams'],
  where: 'Teams.Name = "G2 Esports"',
})
```

**Python (Our Implementation):**
```python
# Built-in filter
teams = await conn.get_teams(region='LEC', limit=50)

# Advanced custom query
teams = await conn._cargo_query(
    tables=['Teams'],
    where='Teams.Name = "G2 Esports"',
    limit=1
)
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/teams?region=LEC
```

---

### JOIN Queries

**TypeScript (Original Poro):**
```typescript
const broadcastMusicUsages = await cargo.query({
  tables: ['BroadcastMusicUsages', 'BroadcastMusicTracks'],
  joinOn: [
    {
      left: 'BroadcastMusicUsages.TrackID',
      right: 'BroadcastMusicTracks.TrackID',
    },
  ],
})
```

**Python (Our Implementation):**
```python
# Get team with full roster (JOIN example)
team_data = await conn.get_team_with_roster(team_name='G2 Esports')
# Returns: {'name': 'G2 Esports', 'roster': [...], ...}

# Advanced custom JOIN
results = await conn._cargo_query(
    tables=['Teams', 'Players'],
    fields=['Teams.Name', 'Players.Player', 'Players.Role'],
    join_on=[{'left': 'Teams.Name', 'right': 'Players.Team'}],
    where='Teams.Region = "LEC"',
    limit=100
)
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/team-roster?team_name=G2%20Esports
```

---

### GROUP BY and HAVING

**TypeScript (Original Poro):**
```typescript
const proplayers = await cargo.query({
  tables: ['Pentakills'],
  groupBy: ['Pentakills.Name'],
  having: 'COUNT(DateDisplay) > 10',
})
```

**Python (Our Implementation):**
```python
# Get players with 10+ pentakills
prolific_players = await conn.get_prolific_pentakill_players(
    min_pentakills=10,
    limit=50
)
# Returns: [{'player': 'Faker', 'pentakill_count': 15, ...}, ...]

# Advanced custom GROUP BY
results = await conn._cargo_query(
    tables=['Pentakills'],
    fields=['Pentakills.Name', 'COUNT(Pentakills.Date) AS Count'],
    group_by=['Pentakills.Name'],
    order_by=[{'field': 'Count', 'desc': True}],
    limit=50
)
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/prolific-pentakills?min_pentakills=10
```

---

## Riot Games API Integration

### Ranked League Entries

**TypeScript (Original Poro):**
```typescript
import { RiotClient, Riot } from 'poro'

const riot = new RiotClient({
  auth: 'RIOT-API-KEY',
  platform: Riot.Platform.KR,
  region: Riot.Region.ASIA,
})

const leagueEntries = await riot
  .path('/lol/league-exp/v4/entries/{queue}/{tier}/{division}', {
    queue: Riot.Queue.RANKED_SOLO_5x5,
    tier: Riot.Tier.CHALLENGER,
    division: Riot.Division.I,
  })
  .get({ query: { page: 1 } })
```

**Python (Our Implementation):**
```python
from src.connectors.riot_connector import RiotConnector

riot = RiotConnector(platform='KR', region='ASIA')
entries = riot.get_league_entries(
    queue='RANKED_SOLO_5x5',
    tier='CHALLENGER',
    division='I',
    page=1
)
# Returns: [{'summoner_name': 'ShowMaker', 'league_points': 1500, ...}, ...]
```

**REST API:**
```bash
GET http://localhost:8000/api/riot/league-entries?platform=KR&tier=CHALLENGER&queue=RANKED_SOLO_5x5&page=1
```

---

### Summoner Profile

**Python (Our Implementation):**
```python
riot = RiotConnector(platform='NA')
summoner = riot.get_summoner_by_name('Doublelift')
# Returns: {'name': 'Doublelift', 'summoner_level': 500, 'puuid': '...', ...}
```

**REST API:**
```bash
GET http://localhost:8000/api/riot/summoner?summoner_name=Doublelift&platform=NA
```

---

## Advanced Query Patterns

### Tournament Standings with Aggregation

**Python:**
```python
standings = await conn.get_tournament_standings(
    tournament='LEC 2024 Spring',
    limit=20
)
# Returns: [
#   {'team': 'G2 Esports', 'wins': 15, 'losses': 3, 'win_rate': 83.33, ...},
#   {'team': 'Fnatic', 'wins': 14, 'losses': 4, 'win_rate': 77.78, ...},
# ]
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/tournament-standings?tournament=LEC%202024%20Spring
```

---

### Champion Statistics

**Python:**
```python
champion_stats = await conn.get_champion_statistics(
    tournament='LEC 2024 Spring',
    limit=50
)
# Returns: [
#   {'champion': 'Azir', 'pick_count': 45, ...},
#   {'champion': 'Orianna', 'pick_count': 38, ...},
# ]
```

**REST API:**
```bash
GET http://localhost:8000/api/poro/champion-stats?tournament=LEC%202024%20Spring&limit=50
```

---

## API Endpoints

### Basic Poro Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/poro/teams` | GET | Get LoL teams from Leaguepedia |
| `/api/poro/tournaments` | GET | Get LoL tournaments |
| `/api/poro/players` | GET | Get LoL players |
| `/api/poro/matches` | GET | Get LoL match results |
| `/api/poro/pentakills` | GET | Get pentakill achievements |

### Advanced Poro Endpoints (GROUP BY, JOIN)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/poro/prolific-pentakills` | GET | Players with multiple pentakills (GROUP BY) |
| `/api/poro/team-roster` | GET | Team with full roster (JOIN) |
| `/api/poro/tournament-standings` | GET | Tournament standings with W/L records |
| `/api/poro/champion-stats` | GET | Champion pick/ban statistics |

### Riot API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/riot/league-entries` | GET | Ranked league entries (Challenger, etc.) |
| `/api/riot/summoner` | GET | Summoner profile by name |

---

## Usage Examples

### Example 1: Get Top Challenger Players in Korea

```bash
curl "http://localhost:8000/api/riot/league-entries?platform=KR&tier=CHALLENGER&queue=RANKED_SOLO_5x5&page=1"
```

**Response:**
```json
{
  "ok": true,
  "provider": "riot",
  "platform": "KR",
  "tier": "CHALLENGER",
  "count": 300,
  "entries": [
    {
      "summoner_name": "ShowMaker",
      "league_points": 1523,
      "wins": 145,
      "losses": 89,
      "hot_streak": true,
      "provider": "riot"
    }
  ]
}
```

---

### Example 2: Get G2 Esports Roster

```bash
curl "http://localhost:8000/api/poro/team-roster?team_name=G2%20Esports"
```

**Response:**
```json
{
  "ok": true,
  "provider": "poro",
  "team": {
    "name": "G2 Esports",
    "region": "LEC",
    "roster": [
      {"name": "BrokenBlade", "role": "Top", "country": "Germany"},
      {"name": "Yike", "role": "Jungle", "country": "China"},
      {"name": "Caps", "role": "Mid", "country": "Denmark"},
      {"name": "Hans sama", "role": "Bot", "country": "France"},
      {"name": "Mikyx", "role": "Support", "country": "Slovenia"}
    ],
    "roster_size": 5
  }
}
```

---

### Example 3: Get Players with 10+ Pentakills

```bash
curl "http://localhost:8000/api/poro/prolific-pentakills?min_pentakills=10&limit=20"
```

**Response:**
```json
{
  "ok": true,
  "provider": "poro",
  "min_pentakills": 10,
  "count": 8,
  "players": [
    {"player": "Faker", "pentakill_count": 15, "provider": "poro"},
    {"player": "Uzi", "pentakill_count": 12, "provider": "poro"},
    {"player": "Rekkles", "pentakill_count": 11, "provider": "poro"}
  ]
}
```

---

### Example 4: Get LEC 2024 Spring Standings

```bash
curl "http://localhost:8000/api/poro/tournament-standings?tournament=LEC%202024%20Spring"
```

**Response:**
```json
{
  "ok": true,
  "provider": "poro",
  "tournament": "LEC 2024 Spring",
  "count": 10,
  "standings": [
    {
      "team": "G2 Esports",
      "wins": 15,
      "losses": 3,
      "matches": 18,
      "win_rate": 83.33,
      "tournament": "LEC 2024 Spring"
    },
    {
      "team": "Fnatic",
      "wins": 14,
      "losses": 4,
      "matches": 18,
      "win_rate": 77.78,
      "tournament": "LEC 2024 Spring"
    }
  ]
}
```

---

## Query Parameters Reference

### Poro Endpoints

#### `/api/poro/teams`
- `region` (optional): Filter by region (LEC, LCS, LCK, LPL, etc.)
- `limit` (optional): Max results (default 50)

#### `/api/poro/tournaments`
- `year` (optional): Filter by year
- `region` (optional): Filter by region
- `limit` (optional): Max results (default 50)

#### `/api/poro/players`
- `team` (optional): Filter by team name
- `role` (optional): Filter by role (Top, Jungle, Mid, Bot, Support)
- `limit` (optional): Max results (default 50)

#### `/api/poro/matches`
- `tournament` (optional): Filter by tournament name
- `team` (optional): Filter by team name
- `limit` (optional): Max results (default 50)

#### `/api/poro/pentakills`
- `player` (optional): Filter by player name
- `limit` (optional): Max results (default 50)

#### `/api/poro/prolific-pentakills`
- `min_pentakills` (optional): Minimum pentakills (default 10)
- `limit` (optional): Max results (default 50)

#### `/api/poro/team-roster`
- `team_name` (required): Team name

#### `/api/poro/tournament-standings`
- `tournament` (required): Tournament name
- `limit` (optional): Max teams (default 20)

#### `/api/poro/champion-stats`
- `tournament` (optional): Filter by tournament
- `limit` (optional): Max champions (default 50)

### Riot API Endpoints

#### `/api/riot/league-entries`
- `queue` (optional): Queue type (default RANKED_SOLO_5x5)
- `tier` (optional): Tier (default CHALLENGER)
- `division` (optional): Division (default I)
- `page` (optional): Page number (default 1)
- `platform` (optional): Platform region (default NA)

**Supported Platforms:**
- NA, EUW, EUNE, KR, BR, LAN, LAS, OCE, TR, RU, JP

**Supported Tiers:**
- CHALLENGER, GRANDMASTER, MASTER, DIAMOND, PLATINUM, GOLD, SILVER, BRONZE, IRON

**Supported Queues:**
- RANKED_SOLO_5x5, RANKED_FLEX_SR, RANKED_FLEX_TT

#### `/api/riot/summoner`
- `summoner_name` (required): Summoner name
- `platform` (optional): Platform region (default NA)

---

## Python Code Examples

### Direct Connector Usage

```python
import asyncio
from src.connectors.poro_connector import get_poro_connector
from src.connectors.riot_connector import RiotConnector

async def main():
    # Poro (Leaguepedia) queries
    poro = await get_poro_connector()
    
    # Get all LEC teams
    lec_teams = await poro.get_teams(region='LEC', limit=10)
    print(f"Found {len(lec_teams)} LEC teams")
    
    # Get G2 roster with JOIN
    g2_roster = await poro.get_team_with_roster('G2 Esports')
    print(f"G2 has {g2_roster['roster_size']} players")
    
    # Get prolific pentakill players with GROUP BY
    penta_kings = await poro.get_prolific_pentakill_players(min_pentakills=10)
    print(f"Found {len(penta_kings)} players with 10+ pentakills")
    
    # Riot API queries
    riot = RiotConnector(platform='KR', region='ASIA')
    
    # Get Challenger ladder
    challengers = riot.get_league_entries(
        queue='RANKED_SOLO_5x5',
        tier='CHALLENGER',
        page=1
    )
    print(f"Found {len(challengers)} Challenger players")
    
    await poro.close()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Environment Variables

```bash
# Optional: Riot API key for enhanced features
RIOT_API_TOKEN=RGAPI-your-key-here

# No API key needed for Leaguepedia (Poro) - it's a public wiki API!
```

---

## Key Differences: TypeScript vs Python

| Feature | TypeScript (Poro npm) | Python (Our Implementation) |
|---------|----------------------|----------------------------|
| Language | JavaScript/TypeScript | Python 3.13+ |
| HTTP Client | axios | aiohttp |
| Async Model | Promises | async/await (native) |
| Type Safety | TypeScript interfaces | Pydantic models + type hints |
| Installation | `npm i poro` | Built-in, no external package needed |
| API Access | Direct library import | REST API + direct connector import |
| Caching | Manual | Automatic (60s TTL) |
| Rate Limiting | Manual | Automatic retry with backoff |

---

## Performance Considerations

- **Caching**: All Poro queries cached for 60 seconds
- **Rate Limiting**: Automatic retry with exponential backoff
- **Timeouts**: Configurable, default 10 seconds
- **Connection Pooling**: aiohttp session reuse
- **Concurrent Requests**: Fully async, non-blocking

---

## Error Handling

All endpoints return consistent error format:

```json
{
  "ok": false,
  "error": "Error message here",
  "hint": "Set RIOT_API_TOKEN environment variable"
}
```

Success responses:

```json
{
  "ok": true,
  "provider": "poro",
  "count": 10,
  "data": [...]
}
```

---

## Next Steps

1. **Set up Riot API key** (optional): Get one from https://developer.riotgames.com/
2. **Start the server**: `python -m uvicorn src.fastapi_app:app --reload --port 8000`
3. **Test endpoints**: Use curl, Postman, or the web interface
4. **Explore data**: Try different regions, tournaments, and players

---

## Support

- **Leaguepedia API Docs**: https://lol.fandom.com/wiki/Special:CargoQuery
- **Riot API Docs**: https://developer.riotgames.com/apis
- **Poro GitHub**: https://github.com/pacexy/poro (TypeScript reference)
- **Our Implementation**: All code in `src/connectors/poro_connector.py` and `src/connectors/riot_connector.py`
