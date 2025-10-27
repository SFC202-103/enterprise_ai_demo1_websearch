"""Convenience script to run an admin sync from the workspace root.

Example:
    python scripts/run_admin_sync.py --connector pandascore --game valorant

This script forwards to `src.admin_cli` so it benefits from the same logic
and tests.
"""
import sys

from src.admin_cli import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
