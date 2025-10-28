"""Admin CLI helper to run connector syncs from the command line.

This module exposes a programmatic `run_sync` function and a CLI entrypoint
that reads `ADMIN_API_KEY` from the environment (or accepts an explicit
`--admin-token` flag) and calls the FastAPI admin_sync implementation.

Usage:
    python -m src.admin_cli --connector pandascore --game valorant

"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, Dict, Optional


def _ensure_token(provided: Optional[str]) -> str:
    token = provided or os.getenv("ADMIN_API_KEY")
    if not token:
        raise ValueError("Admin token required: set ADMIN_API_KEY or pass --admin-token")
    return token


def run_sync(connector: str, game: Optional[str] = None, admin_token: Optional[str] = None) -> Dict[str, Any]:
    """Run the admin sync flow (programmatic).

    Returns the result dict from `admin_sync_impl`.
    """
    token = _ensure_token(admin_token)

    # Import inside function to avoid import-time issues in tests
    from src.fastapi_app import admin_sync_impl

    payload = {"connector": connector, "game": game}
    return asyncio.run(admin_sync_impl(payload, token))


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run admin connector sync")
    p.add_argument("--connector", required=True, help="Connector name (pandascore|riot)")
    p.add_argument("--game", required=False, help="Optional game filter")
    p.add_argument("--admin-token", required=False, help="Admin API token (overrides ADMIN_API_KEY env var)")

    args = p.parse_args(argv)
    try:
        res = run_sync(args.connector, args.game, args.admin_token)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2

    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    # Running as a script should exit with the main return code. Exclude
    # this path from coverage since tests exercise `main()` directly.
    raise SystemExit(main())  # pragma: no cover
