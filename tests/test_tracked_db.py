from src import db


def test_set_and_get_tracked_selection(tmp_path, monkeypatch):
    # Use a temporary SQLite file for this test
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    # Recreate engine/session with new env var by reloading module
    import importlib

    importlib.reload(db)

    db.init_db()

    # Initially empty
    tracked = db.get_tracked_selection()
    assert tracked == {}

    # Set a tracked selection and retrieve it
    res = db.set_tracked_selection("m42", "Team Foo")
    assert res.get("match_id") == "m42"
    assert res.get("team") == "Team Foo"

    got = db.get_tracked_selection()
    assert got.get("match_id") == "m42"
    assert got.get("team") == "Team Foo"
