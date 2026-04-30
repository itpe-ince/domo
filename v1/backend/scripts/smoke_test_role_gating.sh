#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — editor-role-gating (#1 sub-PDCA)
# ─────────────────────────────────────────────────────────
# Verifies:
#   1) Non-artist user gets 403 when creating type=product post
#   2) Artist user gets 200/201 for type=product post
#   3) Non-artist user gets 200/201 for type=general post
#
# Backend role guard location: api/posts.py:206-210
#
# Usage:
#   ./smoke_test_role_gating.sh
#
# Prerequisites:
#   - Backend running on $API (default: http://localhost:3710/v1)
#   - Two test accounts ready:
#       * USER_TOKEN  — access_token of a regular user (role="user")
#       * ARTIST_TOKEN — access_token of an artist (role="artist")
#     (Get tokens via mock login flow or /auth/sns/google in dev)
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
USER_TOKEN="${USER_TOKEN:-}"
ARTIST_TOKEN="${ARTIST_TOKEN:-}"

if [ -z "$USER_TOKEN" ] || [ -z "$ARTIST_TOKEN" ]; then
  echo "Error: USER_TOKEN and ARTIST_TOKEN env vars required."
  echo "Example:"
  echo "  USER_TOKEN=eyJ... ARTIST_TOKEN=eyJ... ./smoke_test_role_gating.sh"
  exit 2
fi

PASS=0
FAIL=0

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

post_create() {
  local token="$1" type="$2"
  local body
  body=$(cat <<JSON
{
  "type": "${type}",
  "title": "smoke-test-${type}",
  "content": "smoke test"$([ "$type" = "product" ] && echo ',
  "genre": "painting",
  "product": {"is_auction": true, "is_buy_now": false}' || echo "")
}
JSON
)
  curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${API}/posts" \
    -H "Authorization: Bearer ${token}" \
    -H "Content-Type: application/json" \
    -d "$body"
}

echo "Test 1 — Non-artist user POST type=product → expect 403"
status=$(post_create "$USER_TOKEN" "product")
assert_status "non-artist + product" "403" "$status"

echo ""
echo "Test 2 — Artist user POST type=product → expect 200 or 201"
status=$(post_create "$ARTIST_TOKEN" "product")
if [ "$status" = "200" ] || [ "$status" = "201" ]; then
  echo "  ✓ artist + product: ${status}"
  PASS=$((PASS + 1))
else
  echo "  ✗ artist + product: expected 200/201, got ${status}"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "Test 3 — Non-artist user POST type=general → expect 200 or 201"
status=$(post_create "$USER_TOKEN" "general")
if [ "$status" = "200" ] || [ "$status" = "201" ]; then
  echo "  ✓ non-artist + general: ${status}"
  PASS=$((PASS + 1))
else
  echo "  ✗ non-artist + general: expected 200/201, got ${status}"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
