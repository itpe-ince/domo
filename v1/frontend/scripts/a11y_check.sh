#!/usr/bin/env bash
# a11y_check.sh — axe-core automated accessibility audit (G'-3, Phase 7)
#
# Prerequisites:
#   1. Run `npm install` in this directory (installs @axe-core/cli from devDependencies)
#   2. Start the dev server: `npm run dev` (default: http://localhost:3000)
#
# Usage:
#   ./scripts/a11y_check.sh                     # default base URL
#   BASE_URL=http://localhost:3001 ./scripts/a11y_check.sh
#
# CI integration: Phase 7 G'-3 carry-over (see docs/03-analysis/i18n-a11y-audit-v0.3.md)
#
# axe-core rules enforced: wcag2a, wcag2aa (WCAG 2.1 AA)
# Exit code: 0 = all pages pass, 1 = violations found

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3000}"
AXE="npx axe"
RULES="--tags wcag2a,wcag2aa"
EXIT_CODE=0

PAGES=(
  "/"
  "/feed"
  "/explore"
  "/notifications"
)

echo "============================================"
echo " Domo a11y audit — axe-core WCAG 2.1 AA"
echo " Base URL: $BASE_URL"
echo "============================================"

for page in "${PAGES[@]}"; do
  url="${BASE_URL}${page}"
  echo ""
  echo "--- Auditing: $url ---"
  if ! $AXE "$url" $RULES; then
    echo "[FAIL] $url"
    EXIT_CODE=1
  fi
done

echo ""
echo "============================================"
if [ $EXIT_CODE -eq 0 ]; then
  echo " All pages passed WCAG 2.1 AA audit."
else
  echo " Violations found. See output above."
fi
echo "============================================"

exit $EXIT_CODE
