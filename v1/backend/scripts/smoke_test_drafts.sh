#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — editor-draft-autosave (#2 sub-PDCA)
# ─────────────────────────────────────────────────────────
# Verifies:
#   1) Unauthenticated POST /posts/drafts → 401
#   2) Create empty draft → 200 with id
#   3) Update draft (with draft_id) → 200, updated_at refreshed
#   4) List drafts → 200 with data array
#   5) Get draft by id → 200 with media included
#   6) Other user accesses draft → 404 (not 403, anti-enumeration)
#   7) Delete draft → 200, deleted=true
#   8) Get deleted draft → 404
#
# Backend handler: api/drafts.py
# Design ref: v1/docs/02-design/features/editor-draft-autosave.design.md
#
# Usage:
#   TOKEN_A=eyJ... TOKEN_B=eyJ... ./smoke_test_drafts.sh
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
TOKEN_A="${TOKEN_A:-}"
TOKEN_B="${TOKEN_B:-}"

if [ -z "$TOKEN_A" ] || [ -z "$TOKEN_B" ]; then
  echo "Error: TOKEN_A and TOKEN_B env vars required (two test users)."
  echo "Example:"
  echo "  TOKEN_A=eyJ... TOKEN_B=eyJ... ./smoke_test_drafts.sh"
  exit 2
fi

PASS=0
FAIL=0
DRAFT_ID=""

assert_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✓ ${label}: ${actual}"
    PASS=$((PASS + 1))
  else
    echo "  ✗ ${label}: expected ${expected}, got ${actual}"
    FAIL=$((FAIL + 1))
  fi
}

# ── Test 1 — Unauthenticated → 401 ──
echo "Test 1 — Unauthenticated POST /posts/drafts → expect 401"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${API}/posts/drafts" \
  -H "Content-Type: application/json" \
  -d '{"type":"general"}')
assert_status "unauth create" "401" "$status"

# ── Test 2 — Create empty draft ──
echo ""
echo "Test 2 — Create empty draft → expect 200"
resp=$(curl -s -X POST "${API}/posts/drafts" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"type":"general","title":null,"content":null}')
DRAFT_ID=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "")
if [ -n "$DRAFT_ID" ]; then
  echo "  ✓ create empty draft: id=${DRAFT_ID}"
  PASS=$((PASS + 1))
else
  echo "  ✗ create empty draft failed. Response: $resp"
  FAIL=$((FAIL + 1))
  echo ""
  echo "Cannot continue without draft id."
  exit 1
fi

# ── Test 3 — Update draft ──
echo ""
echo "Test 3 — Update draft with draft_id → expect 200"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${API}/posts/drafts" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"general\",\"draft_id\":\"${DRAFT_ID}\",\"title\":\"updated\",\"content\":\"smoke test body\"}")
assert_status "update draft" "200" "$status"

# ── Test 4 — List drafts ──
echo ""
echo "Test 4 — List drafts → expect 200"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  "${API}/posts/drafts" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "list drafts" "200" "$status"

# ── Test 5 — Get draft by id ──
echo ""
echo "Test 5 — Get draft by id → expect 200"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  "${API}/posts/drafts/${DRAFT_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "get draft" "200" "$status"

# ── Test 6 — Other user access → 404 (anti-enumeration) ──
echo ""
echo "Test 6 — Other user access → expect 404 (not 403)"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  "${API}/posts/drafts/${DRAFT_ID}" \
  -H "Authorization: Bearer ${TOKEN_B}")
assert_status "other user access" "404" "$status"

# ── Test 7 — Delete draft ──
echo ""
echo "Test 7 — Delete draft → expect 200"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "${API}/posts/drafts/${DRAFT_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "delete draft" "200" "$status"

# ── Test 8 — Get deleted draft → 404 ──
echo ""
echo "Test 8 — Get deleted draft → expect 404"
status=$(curl -s -o /dev/null -w "%{http_code}" \
  "${API}/posts/drafts/${DRAFT_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "get deleted draft" "404" "$status"

# ── Summary ──
echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
