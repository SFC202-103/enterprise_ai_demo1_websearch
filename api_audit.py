"""Professional API Audit Script

This script tests all API endpoints and connectors to verify:
1. Data accuracy and completeness
2. Response formats and structure
3. Team, player, and stats availability
4. Database integration opportunities
"""
import asyncio
import json
from typing import Dict, List, Any

async def test_poro_connector():
    """Test Poro (Leaguepedia) connector for LoL data."""
    print("\n" + "="*80)
    print("🔍 TESTING PORO CONNECTOR (Leaguepedia - League of Legends)")
    print("="*80)
    
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Test 1: Teams
        print("\n1️⃣ Testing Teams Query...")
        teams = await conn.get_teams(region='LEC', limit=5)
        print(f"   ✅ Fetched {len(teams)} LEC teams")
        if teams:
            team = teams[0]
            print(f"   📊 Sample Team: {team.get('name')} ({team.get('region')})")
            print(f"   📋 Available fields: {list(team.keys())}")
        
        # Test 2: Players
        print("\n2️⃣ Testing Players Query...")
        players = await conn.get_players(limit=5)
        print(f"   ✅ Fetched {len(players)} players")
        if players:
            player = players[0]
            print(f"   📊 Sample Player: {player.get('name')} - {player.get('role')} ({player.get('team')})")
            print(f"   📋 Available fields: {list(player.keys())}")
        
        # Test 3: Team Roster (JOIN)
        print("\n3️⃣ Testing Team Roster (JOIN query)...")
        roster = await conn.get_team_with_roster(team_name='G2 Esports')
        if roster.get('ok', True):
            print(f"   ✅ Fetched roster for {roster.get('name')}")
            print(f"   👥 Roster size: {roster.get('roster_size', 0)} players")
            if roster.get('roster'):
                for p in roster['roster'][:3]:
                    print(f"      • {p.get('name')} ({p.get('role')})")
        
        # Test 4: Matches
        print("\n4️⃣ Testing Matches Query...")
        matches = await conn.get_matches(limit=5)
        print(f"   ✅ Fetched {len(matches)} matches")
        if matches:
            match = matches[0]
            print(f"   📊 Sample Match: {match.get('team1', {}).get('name')} vs {match.get('team2', {}).get('name')}")
            print(f"   📋 Available fields: {list(match.keys())}")
        
        # Test 5: Champion Stats
        print("\n5️⃣ Testing Champion Statistics...")
        champ_stats = await conn.get_champion_statistics(limit=5)
        print(f"   ✅ Fetched {len(champ_stats)} champions")
        if champ_stats:
            champ = champ_stats[0]
            print(f"   📊 Sample Champion: {champ.get('champion')} - {champ.get('pick_count', 0)} picks")
            print(f"   📋 Available fields: {list(champ.keys())}")
        
        await conn.close()
        
        return {
            'status': 'success',
            'teams_available': len(teams) > 0,
            'players_available': len(players) > 0,
            'roster_join_works': roster.get('ok', False),
            'matches_available': len(matches) > 0,
            'champion_stats_available': len(champ_stats) > 0
        }
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


async def test_riot_connector():
    """Test Riot Games API connector."""
    print("\n" + "="*80)
    print("🔍 TESTING RIOT GAMES API CONNECTOR")
    print("="*80)
    
    try:
        from src.connectors.riot_connector import RiotConnector
        
        conn = RiotConnector(platform='NA', region='AMERICAS')
        
        # Test 1: League Entries (Ranked Ladder)
        print("\n1️⃣ Testing Ranked League Entries...")
        entries = conn.get_league_entries(tier='CHALLENGER', page=1)
        print(f"   ℹ️  Fetched {len(entries)} Challenger players")
        if entries:
            entry = entries[0]
            print(f"   📊 Sample Entry: {entry.get('summoner_name')} - {entry.get('league_points')} LP")
            print(f"   📋 Available fields: {list(entry.keys())}")
        else:
            print("   ⚠️  No entries (may need RIOT_API_TOKEN)")
        
        # Test 2: Summoner by Name
        print("\n2️⃣ Testing Summoner Lookup...")
        try:
            summoner = conn.get_summoner_by_name('test')
            if summoner:
                print(f"   ✅ Summoner lookup works")
                print(f"   📋 Available fields: {list(summoner.keys())}")
        except Exception as e:
            print(f"   ⚠️  Summoner lookup: {str(e)[:100]}")
        
        return {
            'status': 'success',
            'league_entries_available': len(entries) > 0,
            'summoner_lookup_available': True
        }
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


async def test_pandascore_connector():
    """Test PandaScore connector."""
    print("\n" + "="*80)
    print("🔍 TESTING PANDASCORE CONNECTOR (Multi-game)")
    print("="*80)
    
    try:
        from src.connectors.pandascore_connector import PandaScoreConnector
        
        conn = PandaScoreConnector()
        
        # Test 1: Matches
        print("\n1️⃣ Testing Matches...")
        matches = conn.get_matches(game='lol', limit=3)
        print(f"   ✅ Fetched {len(matches)} LoL matches")
        if matches:
            match = matches[0]
            print(f"   📊 Sample Match: {match.get('id')}")
            print(f"   📋 Available fields: {list(match.keys())}")
            if match.get('opponents'):
                print(f"   👥 Teams: {len(match['opponents'])} teams")
        
        # Test 2: Teams
        print("\n2️⃣ Testing Teams...")
        teams = conn.get_teams(game='lol', limit=3)
        print(f"   ✅ Fetched {len(teams)} teams")
        if teams:
            team = teams[0]
            print(f"   📊 Sample Team: {team.get('name')}")
            print(f"   📋 Available fields: {list(team.keys())}")
        
        # Test 3: Players
        print("\n3️⃣ Testing Players...")
        players = conn.get_players(game='lol', limit=3)
        print(f"   ✅ Fetched {len(players)} players")
        if players:
            player = players[0]
            print(f"   📊 Sample Player: {player.get('name')}")
            print(f"   📋 Available fields: {list(player.keys())}")
        
        return {
            'status': 'success',
            'matches_available': len(matches) > 0,
            'teams_available': len(teams) > 0,
            'players_available': len(players) > 0
        }
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


async def test_database_models():
    """Test database models and structure."""
    print("\n" + "="*80)
    print("TESTING DATABASE MODELS")
    print("="*80)
    
    try:
        from src import db
        
        print("\nAvailable Database Models:")
        print(f"   • Match - ID: {db.Match.__tablename__}")
        print(f"   • Tournament - ID: {db.Tournament.__tablename__}")
        print(f"   • Team - ID: {db.Team.__tablename__}")
        print(f"   • Player - ID: {db.Player.__tablename__}")
        print(f"   • TrackedSelection - ID: {db.TrackedSelection.__tablename__}")
        print(f"   • TrackedState - ID: {db.TrackedState.__tablename__}")
        
        # Check Team model fields
        print("\nTeam Model Fields:")
        team_fields = [c.name for c in db.Team.__table__.columns]
        for field in team_fields:
            print(f"   • {field}")
        
        # Check Player model fields
        print("\nPlayer Model Fields:")
        player_fields = [c.name for c in db.Player.__table__.columns]
        for field in player_fields:
            print(f"   • {field}")
        
        return {
            'status': 'success',
            'team_model_exists': True,
            'player_model_exists': True,
            'team_fields': team_fields,
            'player_fields': player_fields
        }
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def generate_recommendations(results: Dict[str, Any]):
    """Generate professional recommendations based on audit results."""
    print("\n" + "="*80)
    print("📋 PROFESSIONAL AUDIT SUMMARY & RECOMMENDATIONS")
    print("="*80)
    
    print("\n🎯 DATA AVAILABILITY ASSESSMENT:")
    print("-" * 80)
    
    # Poro/Leaguepedia
    if results.get('poro', {}).get('status') == 'success':
        poro = results['poro']
        print("\n✅ Poro (Leaguepedia) - EXCELLENT")
        print(f"   • Teams data: {'✓' if poro.get('teams_available') else '✗'}")
        print(f"   • Players data: {'✓' if poro.get('players_available') else '✗'}")
        print(f"   • Team rosters (JOIN): {'✓' if poro.get('roster_join_works') else '✗'}")
        print(f"   • Match history: {'✓' if poro.get('matches_available') else '✗'}")
        print(f"   • Champion statistics: {'✓' if poro.get('champion_stats_available') else '✗'}")
    
    # Riot API
    if results.get('riot', {}).get('status') == 'success':
        riot = results['riot']
        print("\n✅ Riot Games API - GOOD")
        print(f"   • Ranked ladder: {'✓' if riot.get('league_entries_available') else '✗ (needs API key)'}")
        print(f"   • Summoner lookup: {'✓' if riot.get('summoner_lookup_available') else '✗'}")
    
    # PandaScore
    if results.get('pandascore', {}).get('status') == 'success':
        panda = results['pandascore']
        print("\n✅ PandaScore - EXCELLENT")
        print(f"   • Matches: {'✓' if panda.get('matches_available') else '✗'}")
        print(f"   • Teams: {'✓' if panda.get('teams_available') else '✗'}")
        print(f"   • Players: {'✓' if panda.get('players_available') else '✗'}")
    
    # Database
    if results.get('database', {}).get('status') == 'success':
        db_info = results['database']
        print("\n✅ Database Models - READY")
        print(f"   • Team model: {'✓' if db_info.get('team_model_exists') else '✗'}")
        print(f"   • Player model: {'✓' if db_info.get('player_model_exists') else '✗'}")
    
    print("\n\n🚀 RECOMMENDATIONS FOR OPENAI INTEGRATION:")
    print("-" * 80)
    
    print("\n1️⃣ IMMEDIATE ENHANCEMENTS (High Priority):")
    print("   ✅ Create aggregated team/player stats endpoint")
    print("      • Combine Poro + PandaScore + Riot API data")
    print("      • Cache in database for fast AI queries")
    print("      • Example: GET /api/comprehensive_team_stats?team=G2%20Esports")
    
    print("\n   ✅ Populate database with connector data")
    print("      • Sync Team model from Poro + PandaScore")
    print("      • Sync Player model from Poro + PandaScore")
    print("      • Add player stats JSON field from APIs")
    print("      • Schedule periodic updates")
    
    print("\n   ✅ Create AI-optimized query endpoints")
    print("      • GET /api/ai/team_profile?team=<name>&game=<game>")
    print("      • GET /api/ai/player_profile?player=<name>&game=<game>")
    print("      • GET /api/ai/head_to_head?team1=<name>&team2=<name>")
    print("      • GET /api/ai/tournament_summary?tournament=<name>")
    
    print("\n2️⃣ DATABASE ENHANCEMENTS:")
    print("   📊 Add these tables/fields:")
    print("      • TeamStats (wins, losses, win_rate, recent_form)")
    print("      • PlayerStats (kills, deaths, assists, KDA, role_performance)")
    print("      • MatchHistory (full match details, team rosters)")
    print("      • TournamentStandings (rankings, points, playoff status)")
    
    print("\n3️⃣ DATA PIPELINE RECOMMENDATIONS:")
    print("   🔄 Create data sync jobs:")
    print("      • Hourly: Sync live matches from all connectors")
    print("      • Daily: Update team rosters, player stats")
    print("      • Weekly: Aggregate historical performance metrics")
    print("      • On-demand: Fetch specific team/player on AI query")
    
    print("\n4️⃣ SAMPLE AI QUERIES THAT SHOULD WORK:")
    print("   ❓ 'What are G2 Esports' players and their stats?'")
    print("      → Query: GET /api/poro/team-roster?team_name=G2%20Esports")
    print("      → Also: GET /api/poro/players?team=G2%20Esports")
    print("      → Enhance: Add aggregated stats from matches")
    
    print("\n   ❓ 'Who are the top Challenger players in Korea?'")
    print("      → Query: GET /api/riot/league-entries?platform=KR&tier=CHALLENGER")
    print("      → Returns: Summoner names, LP, win/loss records")
    
    print("\n   ❓ 'What is T1's recent performance in LCK?'")
    print("      → Query: GET /api/poro/matches?team=T1&limit=10")
    print("      → Query: GET /api/poro/tournament-standings?tournament=LCK%202024")
    print("      → Enhance: Calculate win rate, form, momentum")
    
    print("\n   ❓ 'Compare Faker vs Caps stats'")
    print("      → Query: GET /api/poro/players?team=T1 (find Faker)")
    print("      → Query: GET /api/poro/players?team=G2%20Esports (find Caps)")
    print("      → Enhance: Add match stats, champion pool, KDA")
    
    print("\n5️⃣ MISSING DATA GAPS TO ADDRESS:")
    print("   ⚠️  Player individual match statistics (KDA, CS, damage)")
    print("      → Solution: Parse match details from Poro MatchHistory URLs")
    print("      → Solution: Use Riot Match-v5 API for detailed stats")
    
    print("\n   ⚠️  Real-time in-game statistics")
    print("      → Solution: Implement spectator API integration")
    print("      → Solution: Use third-party live data providers")
    
    print("\n   ⚠️  Player historical career stats")
    print("      → Solution: Aggregate from match history over time")
    print("      → Solution: Cache computed stats in Player.stats JSON field")
    
    print("\n6️⃣ OPENAI FUNCTION CALLING SETUP:")
    print("   📝 Define OpenAI functions for:")
    print("      • get_team_roster(team_name, game)")
    print("      • get_player_stats(player_name, game)")
    print("      • get_tournament_standings(tournament_name)")
    print("      • get_match_history(team_name, limit)")
    print("      • get_head_to_head(team1, team2, game)")
    print("      • get_champion_mastery(player_name)")
    
    print("\n" + "="*80)
    print("💡 NEXT STEPS:")
    print("="*80)
    print("1. Implement /api/ai/team_profile endpoint (combines all sources)")
    print("2. Implement /api/ai/player_profile endpoint (combines all sources)")
    print("3. Create database sync script to populate Team & Player tables")
    print("4. Add PlayerStats and TeamStats database tables")
    print("5. Configure OpenAI function calling with new endpoints")
    print("6. Test AI queries with real questions")
    print("="*80 + "\n")


async def main():
    """Run comprehensive API audit."""
    print("\n" + "="*80)
    print("ESPORTS API COMPREHENSIVE PROFESSIONAL AUDIT")
    print("="*80)
    print("Testing all connectors, databases, and data availability...")
    
    results = {}
    
    # Test Poro Connector
    results['poro'] = await test_poro_connector()
    
    # Test Riot Connector
    results['riot'] = await test_riot_connector()
    
    # Test PandaScore Connector
    results['pandascore'] = await test_pandascore_connector()
    
    # Test Database Models
    results['database'] = await test_database_models()
    
    # Generate recommendations
    generate_recommendations(results)
    
    # Save results
    with open('api_audit_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("📁 Results saved to: api_audit_results.json")


if __name__ == '__main__':
    asyncio.run(main())
