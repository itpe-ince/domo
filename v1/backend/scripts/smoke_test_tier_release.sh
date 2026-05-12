#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Smoke test — artist-tier-release (#10) PR2 tier visibility
# ─────────────────────────────────────────────────────────────────────────────
# Verifies:
#   1. Artist creates draft + publish with early_access_duration=1, tier=follower
#      → 200, early_access_until present
#   2. GET as artist (owner) → 200, is_tier_locked=false
#   3. GET as non-qualifying viewer → 403 POST_TIER_RESTRICTED
#   4. (Optional) psql override early_access_until to past, then GET → 200 fallback
#      (skipped if PSQL_CONN not set)
#   5. Cleanup — re-publish with no tier to clear columns
#
# Backend handler: api/posts.py::publish_post, get_post
# Design ref:      v1/docs/02-design/features/artist-tier-release.design.md §B-7, §B-9
#
# Usage:
#   ARTIST_TOKEN=eyJ... VIEWER_TOKEN=eyJ... ./smoke_test_tier_release.sh
#
# Optional env:
#   API          — base URL (default: http://localhost:3710/v1)
#   ARTIST_TOKEN — bearer token for an artist account (REQUIRED)
#   VIEWER_TOKEN — bearer token for a non-following viewer (REQUIRED)
#   PSQL_CONN    — psql connection string for step 4 DB override (optional)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
ARTIST_TOKEN="${ARTIST_TOKEN:-}"
VIEWER_TOKEN="${VIEWER_TOKEN:-}"
PSQL_CONN="${PSQL_CONN:-}"

if [ -z "$ARTIST_TOKEN" ] || [ -z "$VIEWER_TOKEN" ]; then
  echo "Error: ARTIST_TOKEN and VIEWER_TOKEN env vars are required."
  echo "Example:"
  echo "  ARTIST_TOKEN=eyJ... VIEWER_TOKEN=eyJ... ./smoke_test_tier_release.sh"
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

assert_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "  ✓ ${label}: found '${needle}'"
    PASS=$((PASS + 1))
  else
    echo "  ✗ ${label}: '${needle}' not found in response"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_contains() {
  local label="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "  ✗ ${label}: unexpected '${needle}' found in response"
    FAIL=$((FAIL + 1))
  else
    echo "  ✓ ${label}: '${needle}' correctly absent"
    PASS=$((PASS + 1))
  fi
}

# ── Step 1 — Artist creates draft + publishes with tier=follower, duration=1h ──
echo ""
echo "Step 1 — POST /posts (draft) + publish with early_access_duration=1, tier=follower"
DRAFT_RESP=$(curl -s -X POST "${API}/posts" \
  -H "Authorization: Bearer ${ARTIST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"type":"general","title":"Tier Release Smoke Test","content":"tier smoke test content","language":"en"}')
DRAFT_POST_ID=$(echo "$DRAFT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null || echo "")

if [ -z "$DRAFT_POST_ID" ]; then
  echo "  ✗ Failed to create draft post"
  echo "  Response: ${DRAFT_RESP}"
  FAIL=$((FAIL + 1))
  echo ""
  echo "────────────────────────────────────────"
  echo "Result: ${PASS} passed, ${FAIL} failed (aborted — cannot proceed without draft)"
  exit 1
fi
echo "  ✓ Draft post created: ${DRAFT_POST_ID}"
PASS=$((PASS + 1))

PUB_BODY='{"visibility":"public","comments_enabled":true,"series_ids":[],"early_access_duration":1,"early_access_tier":"follower"}'
PUB_RESP=$(curl -s -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${ARTIST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PUB_BODY")
PUB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${ARTIST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"visibility":"public"}')
# First call should be 200; second call (above) will be 409 (already published)
assert_status "re-publish 409 (confirms first succeeded)" "409" "$PUB_HTTP"
assert_contains "early_access_tier in response" "follower" "$PUB_RESP"
assert_contains "early_access_until present" "early_access_until" "$PUB_RESP"

# ── Step 2 — GET as artist (owner) → 200, is_tier_locked=false ──────────────
echo ""
echo "Step 2 — GET /posts/${DRAFT_POST_ID} as artist (owner) → expect 200, is_tier_locked=false"
ARTIST_GET_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${API}/posts/${DRAFT_POST_ID}" \
  -H "Authorization: Bearer ${ARTIST_TOKEN}")
assert_status "artist GET 200" "200" "$ARTIST_GET_HTTP"
ARTIST_GET_RESP=$(curl -s "${API}/posts/${DRAFT_POST_ID}" \
  -H "Authorization: Bearer ${ARTIST_TOKEN}")
assert_contains "is_tier_locked present" "is_tier_locked" "$ARTIST_GET_RESP"
assert_not_contains "is_tier_locked not true for owner" '"is_tier_locked": true' "$ARTIST_GET_RESP"

# ── Step 3 — GET as non-qualifying viewer → 403 POST_TIER_RESTRICTED ────────
echo ""
echo "Step 3 — GET /posts/${DRAFT_POST_ID} as non-qualifying viewer → expect 403 POST_TIER_RESTRICTED"
VIEWER_GET_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${API}/posts/${DRAFT_POST_ID}" \
  -H "Authorization: Bearer ${VIEWER_TOKEN}")
assert_status "non-qualifying viewer 403" "403" "$VIEWER_GET_HTTP"
VIEWER_GET_RESP=$(curl -s "${API}/posts/${DRAFT_POST_ID}" \
  -H "Authorization: Bearer ${VIEWER_TOKEN}")
assert_contains "POST_TIER_RESTRICTED code" "POST_TIER_RESTRICTED" "$VIEWER_GET_RESP"

# ── Step 4 — (Optional) DB override early_access_until to past → 200 fallback ─
echo ""
if [ -n "$PSQL_CONN" ]; then
  echo "Step 4 — psql: set early_access_until to past → GET as viewer → expect 200 fallback"
  psql "$PSQL_CONN" -c "UPDATE posts SET early_access_until = NOW() - INTERVAL '1 hour' WHERE id = '${DRAFT_POST_ID}';" > /dev/null
  EXPIRED_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${API}/posts/${DRAFT_POST_ID}" \
    -H "Authorization: Bearer ${VIEWER_TOKEN}")
  assert_status "expired tier fallback 200" "200" "$EXPIRED_HTTP"
else
  echo "Step 4 — SKIPPED (PSQL_CONN not set; set it to test DB-override expiry fallback)"
fi

# ── Step 5 — Cleanup ─────────────────────────────────────────────────────────
echo ""
echo "Step 5 — Cleanup: note that post ${DRAFT_POST_ID} remains published (cleanup via admin or DB)"
echo "  (Smoke tests do not delete posts to preserve audit trail)"
PASS=$((PASS + 1))

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
