from src import db


def test_get_tracked_state_branch(tmp_path, monkeypatch):
    db_path = tmp_path / "dbextra.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import importlib

    importlib.reload(db)
    db.init_db()

    # ensure empty branch
    empty = db.get_tracked_state("nope")
    assert empty == {}

    # now set and get
    res = db.set_tracked_state("m200", 5, 6, 7, "ts", "pid")
    assert res["match_id"] == "m200"
    got = db.get_tracked_state("m200")
    assert got["home"] == 5
    assert got["away"] == 6
    assert got["round"] == 7
