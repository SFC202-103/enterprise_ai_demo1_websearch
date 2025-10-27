"""Simple seeder that POSTs demo updates to the backend admin endpoint.

Usage:
    python scripts/seed_updates.py --match m1 --count 10 --interval 2

This uses the stdlib so no extra deps are required.
"""
import argparse
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def push_update(server_url, match_id, update):
    url = server_url.rstrip('/') + '/api/admin/push_update'
    data = json.dumps({'match_id': match_id, 'update': update}).encode('utf-8')
    req = Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=5) as resp:
            return resp.read().decode('utf-8')
    except HTTPError as e:
        return f'HTTPError: {e.code} {e.reason}'
    except URLError as e:
        return f'URLError: {e.reason}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default='http://127.0.0.1:8000', help='Backend base URL')
    parser.add_argument('--match', default='m1', help='Match id to seed')
    parser.add_argument('--count', type=int, default=5, help='Number of updates')
    parser.add_argument('--interval', type=float, default=1.0, help='Seconds between updates')
    args = parser.parse_args()

    for i in range(args.count):
        update = {'event': 'tick', 'seq': i+1, 'score': [i % 5, (i+1) % 5]}
        res = push_update(args.server, args.match, update)
        print(f'Pushed {i+1}/{args.count}:', res)
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
