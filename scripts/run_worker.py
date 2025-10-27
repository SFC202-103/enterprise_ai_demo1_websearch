"""Run the background sync worker from the command line.

Usage:
    python scripts/run_worker.py --interval 30
"""
import sys

from src.sync_worker import start_worker


def main(argv=None):
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=int, default=60, help="seconds between syncs")
    args = p.parse_args(argv)

    start_worker(interval=args.interval)
    print(f"sync worker running (interval={args.interval}s), press Ctrl+C to stop")
    try:
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        print("stopping")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
