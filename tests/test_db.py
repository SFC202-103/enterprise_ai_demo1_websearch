import os

from src.db import init_db, save_matches, get_matches


def test_db_save_and_query():
    # Use in-memory sqlite (default)
    init_db()
    sample = [{"id": "mdb1", "title": "DB Match", "scheduled_time": "2025-10-27T00:00:00Z"}]
    saved = save_matches(sample)
    assert saved == 1
    rows = get_matches()
    assert any(r["id"] == "mdb1" for r in rows)
