#!/usr/bin/env bash
# Start only the infrastructure containers (Postgres + Redis).
# Backend and Frontend will run on the host via dev-backend.sh / dev-frontend.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$V1_DIR"

if ! command -v docker >/dev/null 2>&1; then
    echo "❌ docker not found. Install Docker Desktop or OrbStack first." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker daemon is not running. Start Docker Desktop / OrbStack first." >&2
    exit 1
fi

# Stop the docker-managed backend/frontend if they are running
# (we will run them locally instead).
RUNNING_BACKEND="$(docker ps --format '{{.Names}}' | grep -E '^domo_backend$' || true)"
RUNNING_FRONTEND="$(docker ps --format '{{.Names}}' | grep -E '^domo_frontend$' || true)"

if [ -n "$RUNNING_BACKEND" ]; then
    echo "→ Stopping docker-managed backend (local backend will take over)..."
    docker compose stop backend >/dev/null
fi
if [ -n "$RUNNING_FRONTEND" ]; then
    echo "→ Stopping docker-managed frontend (local frontend will take over)..."
    docker compose stop frontend >/dev/null
fi

echo "→ Starting postgres + redis..."
docker compose up -d postgres redis

echo "→ Waiting for postgres to become healthy..."
for _ in $(seq 1 30); do
    STATUS="$(docker inspect --format='{{.State.Health.Status}}' domo_postgres 2>/dev/null || echo starting)"
    if [ "$STATUS" = "healthy" ]; then
        break
    fi
    sleep 1
done

echo "✓ Infra ready"
echo "  Postgres → localhost:55432 (user: domo, db: domo)"
echo "  Redis    → localhost:56379"
