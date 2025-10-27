from src import db


def test_tournament_to_dict():
    t = db.Tournament(id="t1", name="Championship", game="valorant", start_date="2025-10-01", end_date="2025-10-10")
    d = t.to_dict()
    assert d["id"] == "t1"
    assert d["name"] == "Championship"


def test_team_and_player_to_dict():
    team = db.Team(id="team1", name="Blue", short_name="BLU")
    p = db.Player(id="p1", name="Player One", gamertag="p1tag", team_id="team1", role="carry")
    td = team.to_dict()
    pd = p.to_dict()
    assert td["id"] == "team1"
    assert td["short_name"] == "BLU"
    assert pd["id"] == "p1"
    assert pd["team_id"] == "team1"
