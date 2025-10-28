#!/usr/bin/env bash
# Run integration tests inside Docker using the pytest-run service
# Usage: ./scripts/run_integration_in_docker.sh

set -euo pipefail

echo "Bringing up Redis..."
docker compose up -d redis

echo "Running integration tests inside container (pytest-run)..."
docker compose run --rm pytest-run

echo "Done. Tear down with: docker compose down"
