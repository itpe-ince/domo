#!/usr/bin/env bash
# Run alembic migrations against the local infra (postgres on port 55432).
# Useful when schema changes but you don't want to restart the backend.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$V1_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ venv not found at $VENV_DIR" >&2
    echo "   Run scripts/dev-backend.sh once first to bootstrap." >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://domo:domo_dev_pw@localhost:55432/domo}"

cd "$BACKEND_DIR"

case "${1:-upgrade}" in
    upgrade)
        alembic upgrade head
        ;;
    downgrade)
        alembic downgrade -1
        ;;
    current)
        alembic current
        ;;
    history)
        alembic history
        ;;
    *)
        echo "Usage: dev-migrate.sh [upgrade|downgrade|current|history]" >&2
        exit 1
        ;;
esac
