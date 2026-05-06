#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# G''-3 n-plus-one-audit: Response time baseline measurement
#
# Measures p50/p95/p99 latency for 10 core endpoints using `hey` HTTP load tool.
# Requires a running backend (local or staging).
#
# Usage:
#   ./scripts/perf_baseline.sh [BASE_URL] [REQUESTS] [CONCURRENCY]
#
# Defaults:
#   BASE_URL     = http://localhost:3710/v1
#   REQUESTS     = 100
#   CONCURRENCY  = 5
#
# Env vars:
#   AUTH_TOKEN   = Bearer token for authenticated endpoints
#   BASE_URL     = override base URL
#
# Output:
#   Prints p50/p95/p99 per endpoint + summary table
#   Optionally writes to docs/operations/db-performance.md (set WRITE_DOCS=1)
#
# Prerequisites:
#   hey (https://github.com/rakyll/hey):
#     go install github.com/rakyll/hey@latest
#   OR use brew:
#     brew install hey
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3710/v1}"
REQUESTS="${1:-100}"
CONCURRENCY="${2:-5}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
WRITE_DOCS="${WRITE_DOCS:-0}"

if ! command -v hey &>/dev/null; then
    echo "ERROR: 'hey' not found. Install with: brew install hey"
    echo "       or: go install github.com/rakyll/hey@latest"
    exit 1
fi

declare -a ENDPOINT_LABELS=()
declare -a ENDPOINT_P50=()
declare -a ENDPOINT_P95=()
declare -a ENDPOINT_P99=()

measure() {
    local label="$1"
    local url="$2"
    local auth_flag=""
    if [[ -n "$AUTH_TOKEN" ]]; then
        auth_flag="-H \"Authorization: Bearer $AUTH_TOKEN\""
    fi

    echo "── $label ──"
    local output
    if [[ -n "$AUTH_TOKEN" ]]; then
        output=$(hey -n "$REQUESTS" -c "$CONCURRENCY" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            "$url" 2>&1)
    else
        output=$(hey -n "$REQUESTS" -c "$CONCURRENCY" "$url" 2>&1)
    fi

    # Extract percentiles from hey output
    local p50 p95 p99
    p50=$(echo "$output" | grep "50%" | awk '{print $2}' | head -1)
    p95=$(echo "$output" | grep "95%" | awk '{print $2}' | head -1)
    p99=$(echo "$output" | grep "99%" | awk '{print $2}' | head -1)

    echo "  p50=${p50}s  p95=${p95}s  p99=${p99}s"
    echo ""

    ENDPOINT_LABELS+=("$label")
    ENDPOINT_P50+=("${p50:-N/A}")
    ENDPOINT_P95+=("${p95:-N/A}")
    ENDPOINT_P99+=("${p99:-N/A}")
}

echo "=== G''-3 Response Time Baseline ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
echo "Target: $BASE_URL"
echo "Requests: $REQUESTS  Concurrency: $CONCURRENCY"
echo ""

# ── Public endpoints (no auth required) ──────────────────────────────────────
measure "GET /posts/explore (public feed)" \
    "$BASE_URL/posts/explore?limit=20"

measure "GET /posts/explore?sort=popular (trending)" \
    "$BASE_URL/posts/explore?sort=popular&limit=20"

measure "GET /posts/search?q=art" \
    "$BASE_URL/posts/search?q=art&limit=20"

measure "GET /search?q=art (A-5 search v2)" \
    "$BASE_URL/search?q=art&limit=20"

measure "GET /search/popular (A-5 popular)" \
    "$BASE_URL/search/popular"

measure "GET /media-coverage?locale=ko (C-4)" \
    "$BASE_URL/media-coverage?locale=ko&limit=20"

measure "GET /media-coverage/featured" \
    "$BASE_URL/media-coverage/featured?locale=ko"

# ── Authenticated endpoints (requires AUTH_TOKEN) ─────────────────────────────
if [[ -n "$AUTH_TOKEN" ]]; then
    measure "GET /posts/feed (home feed)" \
        "$BASE_URL/posts/feed?limit=20"

    measure "GET /posts/feed?algo=v1 (A-3 personalized)" \
        "$BASE_URL/posts/feed?algo=v1&limit=20"

    measure "GET /notifications?unread_only=true" \
        "$BASE_URL/notifications?unread_only=true&limit=30"
else
    echo "── Authenticated endpoints skipped (AUTH_TOKEN not set) ──"
    echo "   Set AUTH_TOKEN=<bearer_token> to measure authenticated endpoints"
    echo ""
fi

# ── Summary table ─────────────────────────────────────────────────────────────
echo ""
echo "=== Summary ==="
printf "%-50s %8s %8s %8s\n" "Endpoint" "p50" "p95" "p99"
printf "%-50s %8s %8s %8s\n" "$(printf '%0.s-' {1..50})" "--------" "--------" "--------"
for i in "${!ENDPOINT_LABELS[@]}"; do
    printf "%-50s %8s %8s %8s\n" \
        "${ENDPOINT_LABELS[$i]}" \
        "${ENDPOINT_P50[$i]}" \
        "${ENDPOINT_P95[$i]}" \
        "${ENDPOINT_P99[$i]}"
done

if [[ "$WRITE_DOCS" == "1" ]]; then
    DOCS_FILE="$(dirname "$0")/../../../v1/docs/operations/db-performance.md"
    if [[ -f "$DOCS_FILE" ]]; then
        echo ""
        echo "Appending baseline to $DOCS_FILE ..."
        {
            echo ""
            echo "## Baseline Measurement — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
            echo ""
            echo "| Endpoint | p50 | p95 | p99 |"
            echo "|----------|-----|-----|-----|"
            for i in "${!ENDPOINT_LABELS[@]}"; do
                echo "| ${ENDPOINT_LABELS[$i]} | ${ENDPOINT_P50[$i]} | ${ENDPOINT_P95[$i]} | ${ENDPOINT_P99[$i]} |"
            done
        } >> "$DOCS_FILE"
        echo "Done."
    fi
fi

echo ""
echo "Targets (Phase 8 G'' KPI):"
echo "  p50 <= 100ms  p95 <= 200ms  p99 <= 500ms"
