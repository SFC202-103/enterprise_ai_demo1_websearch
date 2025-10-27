import sys
from types import SimpleNamespace

import pytest


def test_save_skips_missing_id():
    from src import db

    # ensure schema exists for this test
    db.init_db()

    sample = [{"title": "no id"}]
    saved = db.save_matches(sample)
    assert saved == 0


def test_save_raw_fallback(monkeypatch):
    # Provide an unserializable object so json.dumps raises and code uses str(m)
    class Odd:
        def __str__(self):
            return "ODD"

    sample = [{"id": "xodd", "weird": Odd()}]

    from src import db

    # ensure schema exists for this test
    db.init_db()

    saved = db.save_matches(sample)
    assert saved == 1
    # inspect stored raw via SessionLocal
    with db.SessionLocal() as session:
        inst = session.get(db.Match, "xodd")
        assert inst is not None
        assert inst.raw == str(sample[0]) or "ODD" in inst.raw


def test_sync_worker_run_once(monkeypatch):
    # Fake PandaScoreConnector to return sample matches
    sample = [{"id": "s1", "title": "sync1"}]

    class FakePanda:
        def __init__(self, *a, **k):
            pass

        def get_matches(self, *a, **k):
            return sample

    monkeypatch.setitem(sys.modules, "src.connectors.pandascore_connector", SimpleNamespace(PandaScoreConnector=FakePanda))

    from src.sync_worker import run_once
    from src import db

    # ensure db tables exist
    db.init_db()
    saved = run_once()
    assert saved >= 1


def test_save_accepts_match_id_key():
    # ensure save_matches accepts 'match_id' as alternate id key
    from src import db

    # ensure schema exists for this test
    db.init_db()

    sample = [{"match_id": "m_alt", "title": "Alt Match"}]
    saved = db.save_matches(sample)
    assert saved == 1
    with db.SessionLocal() as session:
        inst = session.get(db.Match, "m_alt")
        assert inst is not None
        assert inst.title == "Alt Match"


    def test_save_creates_new_instance_when_absent():
        # Ensure we exercise the branch that constructs a new Match(id=...)
        from src import db

        db.init_db()
        # ensure the test id is absent
        with db.SessionLocal() as session:
            session.query(db.Match).filter(db.Match.id == "new_cov").delete()
            session.commit()

        sample = [{"id": "new_cov", "title": "Created"}]
        saved = db.save_matches(sample)
        assert saved == 1
