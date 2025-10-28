Coverage policy for scheduler/tracker modules

This repository enforces a strict 100% unit test coverage target for CI. Two files in
`src/` are intentionally excluded from the coverage gate:

- `src/tracker_tasks.py` — periodic Celery-friendly emitter that has complex
  integration behavior with Redis/Celery that is expensive to reproduce in
  unit tests.
- `src/tracker_worker.py` — APScheduler-based worker that is typically
  exercised in an integration environment with Redis/Cron/Celery.

Rationale

- Those modules implement runtime behavior that depends on external services
  (Redis, Celery, system scheduler semantics). Writing exhaustive unit tests
  that fully emulate those services duplicates large parts of their behavior
  and adds significant test maintenance cost.
- To keep the fast feedback loop for students and CI stable, the project
  excludes these modules from the strict coverage gate and focuses unit-test
  effort on pure-Python logic and DB helpers instead.

How to include them in coverage (optional)

If you want to include these files in coverage in the future, the recommended
approach is to add an integration test job in CI that starts ephemeral
Redis+Celery (e.g., via docker-compose) and runs a small test suite that
exercises `tracker_tasks` and `tracker_worker` in a controlled environment.

Local commands

Run the normal unit tests and coverage check:

```pwsh
python -m pip install -r requirements.txt
pytest --cov=src --cov-config=.coveragerc
```