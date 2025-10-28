# Run the integration tests inside Docker using the pytest-run service
# Usage: .\scripts\run_integration_in_docker.ps1

Write-Host "Bringing up Redis..."
docker compose up -d redis

Write-Host "Running integration tests inside container (pytest-run)..."
docker compose run --rm pytest-run

Write-Host "Done. You can tear down Redis with: docker compose down"