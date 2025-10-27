import sys
import json

import pytest


def test_run_sync_programmatic(monkeypatch):
    # Provide ADMIN_API_KEY and fake connector to avoid network calls
    monkeypatch.setenv("ADMIN_API_KEY", "cli-key")

    sample = [{"id": "mcli", "title": "CLI Match"}]

    class FakePanda:
        def __init__(self, *args, **kwargs):
            pass

        def get_matches(self, *args, **kwargs):
            return sample

    monkeypatch.setitem(sys.modules, "src.connectors.pandascore_connector", type("M", (), {"PandaScoreConnector": FakePanda}))

    from src.admin_cli import run_sync

    res = run_sync("pandascore")
    assert isinstance(res, dict)
    assert res.get("ok") is True
    assert res.get("pushed") == 1


def test_cli_main_exit_code(monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_API_KEY", "cli-key")

    sample = [{"id": "mcli2", "title": "CLI Match 2"}]

    class FakePanda:
        def __init__(self, *args, **kwargs):
            pass

        def get_matches(self, *args, **kwargs):
            return sample

    monkeypatch.setitem(sys.modules, "src.connectors.pandascore_connector", type("M", (), {"PandaScoreConnector": FakePanda}))

    from src.admin_cli import main

    rc = main(["--connector", "pandascore"])
    assert rc == 0


def test_run_sync_missing_token_raises(monkeypatch):
    # Ensure no ADMIN_API_KEY and no explicit token
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    from src.admin_cli import run_sync

    with pytest.raises(ValueError):
        run_sync("pandascore")


def test_cli_main_handles_run_sync_exception(monkeypatch, capsys):
    # Simulate run_sync raising to exercise main's exception path
    monkeypatch.setenv("ADMIN_API_KEY", "cli-key")

    def fake_run_sync(connector, game=None, admin_token=None):
        raise RuntimeError("boom")

    import src.admin_cli as admin_cli_mod

    monkeypatch.setattr(admin_cli_mod, "run_sync", fake_run_sync)

    rc = admin_cli_mod.main(["--connector", "pandascore"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "boom" in captured.out
