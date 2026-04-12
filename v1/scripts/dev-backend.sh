#!/usr/bin/env bash
# Run the FastAPI backend on the host (Python venv).
# Postgres/Redis should already be running via dev-infra.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$V1_DIR/backend"
VENV_DIR="$BACKEND_DIR/.venv"
UPLOAD_DIR_HOST="$BACKEND_DIR/uploads"

cd "$BACKEND_DIR"

# ─── Python version check ──────────────────────────────────────────────
PYTHON_BIN=""
for candidate in python3.12 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VER=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
        MAJOR="${VER%%.*}"
        MINOR="${VER##*.}"
        if [ "$MAJOR" = "3" ] && [ "$MINOR" -ge 12 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "❌ Python >= 3.12 not found. Install via:" >&2
    echo "     brew install python@3.12" >&2
    exit 1
fi

echo "→ Using $PYTHON_BIN ($("$PYTHON_BIN" --version))"

# ─── venv bootstrap ─────────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating virtualenv at $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Install / upgrade dependencies if not present or forced via FORCE_INSTALL=1
REQ_MARKER="$VENV_DIR/.installed-v4"
if [ ! -f "$REQ_MARKER" ] || [ "${FORCE_INSTALL:-0}" = "1" ]; then
    echo "→ Installing Python dependencies..."
    pip install --upgrade pip >/dev/null
    pip install \
        "fastapi[standard]>=0.115" \
        "uvicorn[standard]>=0.32" \
        "sqlalchemy[asyncio]>=2.0" \
        "asyncpg>=0.30" \
        "alembic>=1.14" \
        "pydantic>=2.10" \
        "pydantic-settings>=2.7" \
        "python-jose[cryptography]>=3.3" \
        "passlib[bcrypt]>=1.7" \
        "python-multipart>=0.0.20" \
        "httpx>=0.28" \
        "redis>=5.2" \
        "google-auth>=2.36" \
        "requests>=2.32" \
        "Pillow>=11.0" \
        "aioboto3>=13.2" \
        "stripe>=11.3"
    touch "$REQ_MARKER"
fi

# ─── Environment for host-side execution ───────────────────────────────
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://domo:domo_dev_pw@localhost:55432/domo}"
export REDIS_URL="${REDIS_URL:-redis://localhost:56379/0}"
export JWT_SECRET="${JWT_SECRET:-local_dev_secret_change_me_in_production}"
export FRONTEND_URL="${FRONTEND_URL:-http://localhost:3700}"
export UPLOAD_DIR="${UPLOAD_DIR:-$UPLOAD_DIR_HOST}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export PAYMENT_PROVIDER="${PAYMENT_PROVIDER:-mock_stripe}"
export STORAGE_PROVIDER="${STORAGE_PROVIDER:-local}"
export EMAIL_PROVIDER="${EMAIL_PROVIDER:-mock}"
export RATE_LIMIT_MODE="${RATE_LIMIT_MODE:-enforce}"

mkdir -p "$UPLOAD_DIR"

# Pre-flight infra check
if ! (echo > /dev/tcp/127.0.0.1/55432) >/dev/null 2>&1; then
    echo "❌ Postgres not reachable on localhost:55432. Run:" >&2
    echo "     scripts/dev-infra.sh" >&2
    exit 1
fi
if ! (echo > /dev/tcp/127.0.0.1/56379) >/dev/null 2>&1; then
    echo "❌ Redis not reachable on localhost:56379. Run:" >&2
    echo "     scripts/dev-infra.sh" >&2
    exit 1
fi

# ─── Migrate ───────────────────────────────────────────────────────────
echo "→ Running alembic migrations..."
alembic upgrade head

# ─── Run ───────────────────────────────────────────────────────────────
echo
echo "=================================="
echo "  Backend dev server starting"
echo "  URL:        http://localhost:3710"
echo "  API docs:   http://localhost:3710/docs"
echo "  Health:     http://localhost:3710/v1/health"
echo "  Uploads:    $UPLOAD_DIR"
echo "=================================="
echo

exec uvicorn app.main:app --host 0.0.0.0 --port 3710 --reload
