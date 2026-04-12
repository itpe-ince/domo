#!/usr/bin/env bash
# Run the seed scripts against the local infra.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$V1_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ venv not found. Run scripts/dev-backend.sh once first." >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://domo:domo_dev_pw@localhost:5432/domo}"
export UPLOAD_DIR="${UPLOAD_DIR:-$BACKEND_DIR/uploads}"

cd "$BACKEND_DIR"

TARGET="${1:-all}"

case "$TARGET" in
    base|seed)
        echo "→ Running base seed..."
        python -m scripts.seed
        ;;
    demo)
        echo "→ Running demo seed..."
        python -m scripts.seed_demo
        ;;
    all)
        echo "→ Running base seed..."
        python -m scripts.seed
        echo
        echo "→ Running demo seed..."
        python -m scripts.seed_demo
        ;;
    *)
        echo "Usage: dev-seed.sh [all|base|demo]" >&2
        exit 1
        ;;
esac
