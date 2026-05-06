#!/usr/bin/env bash
# lighthouse_check.sh — G''-5 bundle-optimization
#
# Runs Lighthouse audits against 5 core Domo pages.
# Requires: `lighthouse` CLI installed (npm install -g lighthouse)
# Requires: frontend dev/prod server running on localhost:3000
#
# Usage:
#   npm run build && npm run start &
#   bash scripts/lighthouse_check.sh
#
# Output:
#   JSON reports written to lighthouse-reports/ directory.
#   Summary scores printed to stdout.
#
# Targets:
#   Performance:     >= 80
#   Accessibility:   >= 90
#   Best Practices:  >= 90
#   SEO:             >= 90

set -euo pipefail

REPORT_DIR="lighthouse-reports"
mkdir -p "$REPORT_DIR"

BASE_URL="${LIGHTHOUSE_BASE_URL:-http://localhost:3000}"

PAGES=(
  "/"
  "/feed"
  "/explore"
  "/posts/new"
  "/users/example"
)

PAGE_NAMES=(
  "home"
  "feed"
  "explore"
  "posts-new"
  "user-profile"
)

# Check lighthouse is available
if ! command -v lighthouse &>/dev/null; then
  echo "ERROR: lighthouse not found. Install with: npm install -g lighthouse"
  exit 1
fi

echo "=== Lighthouse Audit ==="
echo "Base URL: $BASE_URL"
echo ""

for i in "${!PAGES[@]}"; do
  PAGE="${PAGES[$i]}"
  NAME="${PAGE_NAMES[$i]}"
  URL="${BASE_URL}${PAGE}"
  OUTFILE="${REPORT_DIR}/lighthouse-${NAME}.json"

  echo "Auditing: $URL"
  lighthouse "$URL" \
    --quiet \
    --chrome-flags="--headless --no-sandbox --disable-dev-shm-usage" \
    --only-categories=performance,accessibility,best-practices,seo \
    --output=json \
    --output-path="$OUTFILE" \
    --skip-audits=uses-http2 \
    2>/dev/null || true

  if [[ -f "$OUTFILE" ]]; then
    PERF=$(node -e "const r=require('./$OUTFILE'); console.log(Math.round((r.categories.performance?.score??0)*100))" 2>/dev/null || echo "N/A")
    A11Y=$(node -e "const r=require('./$OUTFILE'); console.log(Math.round((r.categories.accessibility?.score??0)*100))" 2>/dev/null || echo "N/A")
    BP=$(node -e "const r=require('./$OUTFILE'); console.log(Math.round((r['best-practices']?.score??r.categories['best-practices']?.score??0)*100))" 2>/dev/null || echo "N/A")
    SEO=$(node -e "const r=require('./$OUTFILE'); console.log(Math.round((r.categories.seo?.score??0)*100))" 2>/dev/null || echo "N/A")
    printf "  %-18s Perf: %3s  A11y: %3s  BP: %3s  SEO: %3s\n" "$NAME" "$PERF" "$A11Y" "$BP" "$SEO"
  else
    echo "  $NAME: report not generated (server may not be reachable)"
  fi
done

echo ""
echo "Targets: Performance>=80  Accessibility>=90  BestPractices>=90  SEO>=90"
echo "Reports: $REPORT_DIR/"
