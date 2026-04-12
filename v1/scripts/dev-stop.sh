#!/usr/bin/env bash
# Stop infra containers (postgres + redis).
# Backend and frontend run on the host — press Ctrl+C in their terminals.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$V1_DIR"

echo "→ Stopping postgres + redis..."
docker compose stop postgres redis

echo "✓ Infra stopped"
echo "  Data volumes are preserved — next 'dev-infra.sh' will resume."
