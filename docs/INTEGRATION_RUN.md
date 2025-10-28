Running integration tests locally (Redis + scheduler)

This project includes a small `docker-compose.yml` that starts a Redis service
used by the tracker integration tests. The integration tests are gated so they
won't run by default during normal `pytest` runs — you must opt-in.

Quick steps (PowerShell)

1. Start Redis with Docker Compose:

```pwsh
docker compose up -d
```

2. Install dependencies (if not already):

```pwsh
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Run the integration tests (opt-in):

```pwsh
$env:RUN_INTEGRATION = '1'
$env:REDIS_URL = 'redis://localhost:6379/0'
pytest -q -m integration
```

Notes for Bash/macOS/Linux

```bash
docker compose up -d
python -m pip install --upgrade pip
pip install -r requirements.txt
export RUN_INTEGRATION=1
export REDIS_URL=redis://localhost:6379/0
pytest -q -m integration
```

Optional: run tests inside a container

The `docker-compose.yml` file includes an example `pytest-run` service (commented
out) you can enable to run tests inside a container on the same Docker network
as Redis. Uncomment and adapt the service if you prefer that workflow.

Run tests inside Docker (helper scripts)

Two helper scripts are available under `scripts/` to run the integration
tests inside Docker:

- PowerShell: `scripts/run_integration_in_docker.ps1`
- Bash: `scripts/run_integration_in_docker.sh`

These scripts will start the `redis` service (if needed) and then run the
`pytest-run` service which installs dependencies and runs `pytest -m integration`.

Example (PowerShell):

```pwsh
.\scripts\run_integration_in_docker.ps1
```

Example (bash):

```bash
./scripts/run_integration_in_docker.sh
```

Troubleshooting

- If the integration test skips, ensure `RUN_INTEGRATION=1` is set in your
  environment and `REDIS_URL` points to a running Redis instance.
- If the test cannot import APScheduler or `redis` package, install the missing
  packages into your Python environment (e.g. `pip install apscheduler redis`).
- The integration test uses a temporary SQLite file by default and calls
  `src.db.init_db()`; check `DATABASE_URL` if you need the DB at a custom
  location.

CI note

The GitHub Actions workflow includes an `integration` job that starts Redis
and sets `RUN_INTEGRATION=1` so these tests run in CI without additional setup.

If you'd like, I can add a small `Makefile` target to automate these commands
locally (e.g., `make integration-test`).
