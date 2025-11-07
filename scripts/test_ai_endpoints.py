"""Test AI Endpoints

Test script to verify AI-optimized endpoints work correctly with sample queries.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_endpoints import (
    get_ai_team_profile,
    get_ai_player_profile,
    get_ai_head_to_head,
    get_ai_tournament_summary
)


async def test_team_profile():
    """Test team profile endpoint."""
    print("\n" + "="*80)
    print("TEST 1: Team Profile")
    print("="*80)
    print("\nQuery: 'What are G2 Esports' players?'\n")
    
    result = await get_ai_team_profile(team='G2 Esports', game='lol')
    
    if result.get('ok'):
        print(f"✓ SUCCESS")
        print(f"\nTeam: {result['team']['name']}")
        print(f"Region: {result['team'].get('region', 'N/A')}")
        print(f"Roster Size: {result['team']['roster_size']}")
        
        if result['team']['roster']:
            print(f"\nPlayers:")
            for player in result['team']['roster']:
                print(f"  • {player.get('name')} - {player.get('role')} ({player.get('country', 'Unknown')})")
        
        stats = result.get('statistics', {})
        print(f"\nStatistics:")
        print(f"  • Recent Matches: {stats.get('recent_matches', 0)}")
        print(f"  • Win Rate: {stats.get('win_rate', 0)}%")
        print(f"  • Form: {stats.get('recent_form', 'No data')}")
        print(f"  • Momentum: {stats.get('momentum', 'Unknown')}")
    else:
        print(f"✗ FAILED: {result.get('error')}")
    
    return result


async def test_player_profile():
    """Test player profile endpoint."""
    print("\n" + "="*80)
    print("TEST 2: Player Profile")
    print("="*80)
    print("\nQuery: 'Who is Faker?'\n")
    
    result = await get_ai_player_profile(player='Faker', game='lol')
    
    if result.get('ok'):
        print(f"✓ SUCCESS")
        player = result['player']
        print(f"\nPlayer: {player['name']}")
        print(f"Real Name: {player.get('real_name', 'N/A')}")
        print(f"Role: {player.get('role', 'N/A')}")
        print(f"Team: {player.get('team', 'N/A')}")
        print(f"Country: {player.get('country', 'N/A')}")
        print(f"Age: {player.get('age', 'N/A')}")
        print(f"Status: {player.get('status', 'Unknown')}")
        
        if result.get('team_context'):
            team = result['team_context']
            print(f"\nTeam Context:")
            print(f"  • Team: {team.get('name', 'N/A')}")
            print(f"  • Region: {team.get('region', 'N/A')}")
    else:
        print(f"✗ FAILED: {result.get('error')}")
        if result.get('sample_players'):
            print(f"\nSample available players:")
            for p in result['sample_players'][:5]:
                print(f"  • {p}")
    
    return result


async def test_head_to_head():
    """Test head-to-head comparison."""
    print("\n" + "="*80)
    print("TEST 3: Head-to-Head Comparison")
    print("="*80)
    print("\nQuery: 'Compare G2 Esports vs Fnatic'\n")
    
    result = await get_ai_head_to_head(team1='G2 Esports', team2='Fnatic', game='lol')
    
    if result.get('ok'):
        print(f"✓ SUCCESS")
        h2h = result['head_to_head']
        print(f"\nHead-to-Head Record:")
        print(f"  • Total Matches: {h2h['total_matches']}")
        print(f"  • G2 Esports Wins: {h2h['team1_wins']}")
        print(f"  • Fnatic Wins: {h2h['team2_wins']}")
        
        if h2h['most_recent']:
            print(f"\nMost Recent Match:")
            match = h2h['most_recent']
            print(f"  • {match.get('team1', {}).get('name')} vs {match.get('team2', {}).get('name')}")
            print(f"  • Winner: {match.get('winner', 'Unknown')}")
    else:
        print(f"✗ FAILED: {result.get('error')}")
    
    return result


async def test_tournament_summary():
    """Test tournament summary."""
    print("\n" + "="*80)
    print("TEST 4: Tournament Summary")
    print("="*80)
    print("\nQuery: 'Show LEC 2024 Spring standings'\n")
    
    result = await get_ai_tournament_summary(tournament='LEC 2024 Spring')
    
    if result.get('ok'):
        print(f"✓ SUCCESS")
        stats = result.get('statistics', {})
        print(f"\nTournament: {result['tournament']}")
        print(f"Total Teams: {stats.get('total_teams', 0)}")
        print(f"Leader: {stats.get('current_leader', 'Unknown')}")
        print(f"Leader Record: {stats.get('leader_record', 'N/A')}")
        
        standings = result.get('standings', [])
        if standings:
            print(f"\nStandings (Top 5):")
            for i, team in enumerate(standings[:5], 1):
                print(f"  {i}. {team.get('team')} - {team.get('wins')}-{team.get('losses')} ({team.get('win_rate', 0):.1f}%)")
    else:
        print(f"✗ FAILED: {result.get('error')}")
    
    return result


async def test_sample_queries():
    """Test with realistic AI queries."""
    print("\n" + "="*80)
    print("TESTING REALISTIC AI QUERIES")
    print("="*80)
    
    queries = [
        ("Team Query", "G2 Esports", get_ai_team_profile, {'team': 'G2 Esports'}),
        ("Player Query", "Caps", get_ai_player_profile, {'player': 'Caps'}),
    ]
    
    results = []
    
    for query_type, query_text, func, args in queries:
        print(f"\n{query_type}: '{query_text}'")
        result = await func(**args)
        
        if result.get('ok'):
            print(f"  ✓ SUCCESS - Data available")
        else:
            print(f"  ✗ FAILED - {result.get('error', 'Unknown error')}")
        
        results.append((query_type, result.get('ok', False)))
    
    return results


async def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("AI ENDPOINTS TEST SUITE")
    print("="*80)
    print("\nTesting AI-optimized endpoints for esports data...\n")
    
    # Run individual tests
    test1 = await test_team_profile()
    test2 = await test_player_profile()
    test3 = await test_head_to_head()
    test4 = await test_tournament_summary()
    
    # Run sample query tests
    sample_results = await test_sample_queries()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    tests = [
        ("Team Profile", test1.get('ok', False)),
        ("Player Profile", test2.get('ok', False)),
        ("Head-to-Head", test3.get('ok', False)),
        ("Tournament Summary", test4.get('ok', False))
    ]
    
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    
    for test_name, ok in tests:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed\n")
    
    if passed == total:
        print("All tests passed! AI endpoints are ready for use.")
    else:
        print("Some tests failed. Check error messages above.")
    
    print("\nNext steps:")
    print("1. Start the FastAPI server: python -m uvicorn src.fastapi_app:app --port 8000")
    print("2. Test endpoints via HTTP:")
    print("   curl http://localhost:8000/api/ai/team_profile?team=G2%20Esports")
    print("   curl http://localhost:8000/api/ai/player_profile?player=Faker")
    print("3. Configure OpenAI with function definitions from:")
    print("   curl http://localhost:8000/api/ai/openai_functions")
    print("")


if __name__ == '__main__':
    asyncio.run(main())
