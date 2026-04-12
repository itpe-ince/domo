#!/usr/bin/env bash
# Run the Next.js frontend on the host (Node 20+).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
V1_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FE_DIR="$V1_DIR/frontend"

cd "$FE_DIR"

# ─── Node version check ────────────────────────────────────────────────
if ! command -v node >/dev/null 2>&1; then
    echo "❌ node not found. Install Node 20+ first:" >&2
    echo "     brew install node@20" >&2
    exit 1
fi

NODE_VER="$(node -v | sed 's/^v//')"
NODE_MAJOR="${NODE_VER%%.*}"
if [ "$NODE_MAJOR" -lt 20 ]; then
    echo "❌ Node >= 20 required (found v$NODE_VER)" >&2
    exit 1
fi

echo "→ Using node v$NODE_VER"

# ─── npm install ───────────────────────────────────────────────────────
if [ ! -d node_modules ] || [ "${FORCE_INSTALL:-0}" = "1" ]; then
    echo "→ Installing npm dependencies..."
    npm install
fi

# ─── Env ───────────────────────────────────────────────────────────────
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:3710/v1}"
export NODE_ENV="${NODE_ENV:-development}"

echo
echo "=================================="
echo "  Frontend dev server starting"
echo "  URL:        http://localhost:3700"
echo "  API:        $NEXT_PUBLIC_API_URL"
echo "=================================="
echo

exec npx next dev --port 3700 --hostname 0.0.0.0
