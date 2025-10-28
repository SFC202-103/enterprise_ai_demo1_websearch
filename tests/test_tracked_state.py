from src import db


def test_set_and_get_tracked_state(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    import importlib

    importlib.reload(db)
    db.init_db()

    res = db.set_tracked_state("m99", 1, 2, 3, "ts", "pid")
    assert res["match_id"] == "m99"
    got = db.get_tracked_state("m99")
    assert got["home"] == 1
    assert got["away"] == 2
    assert got["round"] == 3
    assert got["leader_pid"] == "pid"
