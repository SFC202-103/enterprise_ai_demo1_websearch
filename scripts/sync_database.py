"""Database Synchronization Script

Syncs esports data from API connectors into the local database for:
- Faster AI query responses
- Offline data availability
- Historical data persistence
- Reduced API calls

Usage:
    python scripts/sync_database.py --sync-teams --sync-players
    python scripts/sync_database.py --all
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import db


async def sync_teams_to_database(limit: int = 500) -> dict:
    """Sync teams from Poro connector to database.
    
    Args:
        limit: Maximum number of teams to sync
        
    Returns:
        Dictionary with sync statistics
    """
    print(f"\n{'='*80}")
    print("SYNCING TEAMS TO DATABASE")
    print(f"{'='*80}\n")
    
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Fetch all teams
        print(f"Fetching teams from Leaguepedia (limit: {limit})...")
        teams = await conn.get_teams(limit=limit)
        print(f"✓ Fetched {len(teams)} teams")
        
        # Fetch player rosters for teams
        print("\nFetching rosters for each team...")
        teams_with_rosters = []
        
        for i, team in enumerate(teams, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(teams)} teams processed...")
            
            # Try to get roster
            roster_data = await conn.get_team_with_roster(team_name=team['name'])
            
            if roster_data.get('ok', True) and roster_data.get('roster'):
                team['roster'] = roster_data['roster']
                team['roster_size'] = len(roster_data['roster'])
            else:
                team['roster'] = []
                team['roster_size'] = 0
            
            teams_with_rosters.append(team)
        
        await conn.close()
        
        # Insert/update database
        print(f"\nSyncing {len(teams_with_rosters)} teams to database...")
        db.init_db()  # Ensure tables exist
        
        with db.SessionLocal() as session:
            synced_count = 0
            updated_count = 0
            
            for team in teams_with_rosters:
                # Check if team exists
                existing = session.query(db.Team).filter(db.Team.id == team['id']).first()
                
                if existing:
                    # Update existing team
                    existing.name = team['name']
                    existing.short_name = team['acronym']
                    existing.roster_json = json.dumps(team['roster'])
                    updated_count += 1
                else:
                    # Insert new team
                    new_team = db.Team(
                        id=team['id'],
                        name=team['name'],
                        short_name=team['acronym'],
                        roster_json=json.dumps(team['roster'])
                    )
                    session.add(new_team)
                    synced_count += 1
            
            session.commit()
        
        print(f"✓ Synced {synced_count} new teams")
        print(f"✓ Updated {updated_count} existing teams")
        print(f"✓ Total teams in database: {synced_count + updated_count}")
        
        return {
            "ok": True,
            "teams_fetched": len(teams),
            "teams_synced": synced_count,
            "teams_updated": updated_count,
            "total": synced_count + updated_count
        }
        
    except Exception as e:
        print(f"✗ Error syncing teams: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }


async def sync_players_to_database(limit: int = 1000) -> dict:
    """Sync players from Poro connector to database.
    
    Args:
        limit: Maximum number of players to sync
        
    Returns:
        Dictionary with sync statistics
    """
    print(f"\n{'='*80}")
    print("SYNCING PLAYERS TO DATABASE")
    print(f"{'='*80}\n")
    
    try:
        from src.connectors.poro_connector import get_poro_connector
        
        conn = await get_poro_connector()
        
        # Fetch all players
        print(f"Fetching players from Leaguepedia (limit: {limit})...")
        players = await conn.get_players(limit=limit)
        print(f"✓ Fetched {len(players)} players")
        
        await conn.close()
        
        # Insert/update database
        print(f"\nSyncing {len(players)} players to database...")
        db.init_db()  # Ensure tables exist
        
        with db.SessionLocal() as session:
            synced_count = 0
            updated_count = 0
            
            for player in players:
                # Generate player ID
                player_id = player.get('id', f"player_{player['name'].replace(' ', '_').lower()}")
                
                # Check if player exists
                existing = session.query(db.Player).filter(db.Player.id == player_id).first()
                
                # Prepare stats JSON
                stats_json = json.dumps({
                    'role': player.get('role'),
                    'country': player.get('country'),
                    'age': player.get('age'),
                    'retired': player.get('retired', False),
                    'real_name': player.get('real_name'),
                    'native_name': player.get('native_name')
                })
                
                if existing:
                    # Update existing player
                    existing.name = player.get('name')
                    existing.gamertag = player.get('name')
                    existing.team_id = player.get('team')
                    existing.role = player.get('role')
                    existing.stats = stats_json
                    updated_count += 1
                else:
                    # Insert new player
                    new_player = db.Player(
                        id=player_id,
                        name=player.get('name'),
                        gamertag=player.get('name'),
                        team_id=player.get('team'),
                        role=player.get('role'),
                        stats=stats_json
                    )
                    session.add(new_player)
                    synced_count += 1
            
            session.commit()
        
        print(f"✓ Synced {synced_count} new players")
        print(f"✓ Updated {updated_count} existing players")
        print(f"✓ Total players in database: {synced_count + updated_count}")
        
        return {
            "ok": True,
            "players_fetched": len(players),
            "players_synced": synced_count,
            "players_updated": updated_count,
            "total": synced_count + updated_count
        }
        
    except Exception as e:
        print(f"✗ Error syncing players: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }


async def verify_database() -> dict:
    """Verify database contents after sync.
    
    Returns:
        Dictionary with database statistics
    """
    print(f"\n{'='*80}")
    print("VERIFYING DATABASE CONTENTS")
    print(f"{'='*80}\n")
    
    try:
        db.init_db()
        
        with db.SessionLocal() as session:
            team_count = session.query(db.Team).count()
            player_count = session.query(db.Player).count()
            
            print(f"Database Statistics:")
            print(f"  • Teams: {team_count}")
            print(f"  • Players: {player_count}")
            
            # Show sample teams
            if team_count > 0:
                print(f"\nSample Teams (first 5):")
                teams = session.query(db.Team).limit(5).all()
                for team in teams:
                    roster_data = json.loads(team.roster_json) if team.roster_json else []
                    print(f"  • {team.name} ({team.short_name}) - {len(roster_data)} players")
            
            # Show sample players
            if player_count > 0:
                print(f"\nSample Players (first 5):")
                players = session.query(db.Player).limit(5).all()
                for player in players:
                    print(f"  • {player.name} - {player.role} ({player.team_id})")
        
        return {
            "ok": True,
            "teams": team_count,
            "players": player_count
        }
        
    except Exception as e:
        print(f"✗ Error verifying database: {str(e)}")
        return {
            "ok": False,
            "error": str(e)
        }


async def main():
    """Main synchronization function."""
    parser = argparse.ArgumentParser(description='Sync esports data to database')
    parser.add_argument('--sync-teams', action='store_true', help='Sync teams to database')
    parser.add_argument('--sync-players', action='store_true', help='Sync players to database')
    parser.add_argument('--all', action='store_true', help='Sync everything')
    parser.add_argument('--team-limit', type=int, default=500, help='Max teams to sync')
    parser.add_argument('--player-limit', type=int, default=1000, help='Max players to sync')
    parser.add_argument('--verify', action='store_true', help='Verify database after sync')
    
    args = parser.parse_args()
    
    # If no specific sync requested, show help
    if not (args.sync_teams or args.sync_players or args.all or args.verify):
        parser.print_help()
        return
    
    print("\n" + "="*80)
    print("ESPORTS DATABASE SYNCHRONIZATION")
    print("="*80)
    
    results = {}
    
    # Sync teams
    if args.sync_teams or args.all:
        results['teams'] = await sync_teams_to_database(limit=args.team_limit)
    
    # Sync players
    if args.sync_players or args.all:
        results['players'] = await sync_players_to_database(limit=args.player_limit)
    
    # Verify database
    if args.verify or args.all:
        results['verification'] = await verify_database()
    
    # Summary
    print(f"\n{'='*80}")
    print("SYNCHRONIZATION COMPLETE")
    print(f"{'='*80}\n")
    
    if 'teams' in results and results['teams'].get('ok'):
        print(f"✓ Teams: {results['teams']['total']} in database")
    
    if 'players' in results and results['players'].get('ok'):
        print(f"✓ Players: {results['players']['total']} in database")
    
    print("\nDatabase is ready for AI queries!")
    print("Use these endpoints to access the data:")
    print("  • GET /api/ai/team_profile?team=<name>")
    print("  • GET /api/ai/player_profile?player=<name>")
    print("")


if __name__ == '__main__':
    asyncio.run(main())
