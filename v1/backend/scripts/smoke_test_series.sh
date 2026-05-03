#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — publish-controls (#8) Series CRUD
# ─────────────────────────────────────────────────────────
# Verifies:
#   1. POST /series (title="Smoke Test Series") → 201, capture SERIES_ID
#   2. GET /series/{SERIES_ID} → 200, title matches, posts=[]
#   3. POST /posts/{POST_ID}/series (series_ids=[SERIES_ID]) → 200, series_count=1
#      (POST_ID must be a published post owned by TOKEN_A)
#   4. PATCH /series/{SERIES_ID} (title="Updated Title") → 200 (owner OK)
#   5. (optional) PATCH from OTHER_TOKEN → 403 SERIES_NOT_OWNER
#   6. DELETE /series/{SERIES_ID} → 204
#
# Backend handler: api/series.py
# Design ref:      v1/docs/02-design/features/publish-controls.design.md §B-8
#
# Usage:
#   TOKEN_A=eyJ... ./smoke_test_series.sh
#   TOKEN_A=eyJ... POST_ID=<uuid> ./smoke_test_series.sh
#   TOKEN_A=eyJ... OTHER_TOKEN=eyJ... ./smoke_test_series.sh
#
# Optional env:
#   API          — base URL (default: http://localhost:3710/v1)
#   TOKEN_A      — bearer token for owner account (REQUIRED)
#   POST_ID      — existing post UUID to add to series (auto-creates draft if omitted)
#   OTHER_TOKEN  — bearer token for a different account (enables step 5 cross-ownership check)
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
TOKEN_A="${TOKEN_A:-}"
OTHER_TOKEN="${OTHER_TOKEN:-}"
POST_ID="${POST_ID:-}"

if [ -z "$TOKEN_A" ]; then
  echo "Error: TOKEN_A env var required (bearer token for artist account)."
  echo "Example:"
  echo "  TOKEN_A=eyJ... ./smoke_test_series.sh"
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

# ── Ensure we have a POST_ID (auto-create draft if not provided) ──────────
if [ -z "$POST_ID" ]; then
  echo "POST_ID not set — creating a draft post to use for series membership test..."
  DRAFT_RESP=$(curl -s -X POST "${API}/posts" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d '{"type":"general","title":"Series Smoke Draft","content":"draft for series test","language":"en"}')
  POST_ID=$(echo "$DRAFT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null || echo "")
  if [ -z "$POST_ID" ]; then
    echo "  Warning: Could not create draft post. Step 3 will be skipped."
    echo "  Response: ${DRAFT_RESP}"
  else
    echo "  Auto-created draft post: POST_ID=${POST_ID}"
  fi
fi

# ── Step 1 — Create series ────────────────────────────────────────────────
echo ""
echo "Step 1 — POST /series → expect 201"
CREATE_RESP=$(curl -s -X POST "${API}/series" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke Test Series","description":"Created by smoke test"}')
CREATE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/series" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke Test Series 2"}')
assert_status "create_series 201" "201" "$CREATE_HTTP"

SERIES_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null || echo "")
if [ -n "$SERIES_ID" ]; then
  echo "  ✓ Series created: ${SERIES_ID}"
  PASS=$((PASS + 1))
else
  echo "  ✗ Failed to capture SERIES_ID from first create call"
  echo "  Response: ${CREATE_RESP}"
  FAIL=$((FAIL + 1))
  echo ""
  echo "─────────────────────────────────────"
  echo "Result: ${PASS} passed, ${FAIL} failed (aborted — cannot proceed without SERIES_ID)"
  exit 1
fi

# ── Step 2 — GET series detail ────────────────────────────────────────────
echo ""
echo "Step 2 — GET /series/${SERIES_ID} → expect 200 + title matches + posts=[]"
GET_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "get_series 200" "200" "$GET_HTTP"
GET_RESP=$(curl -s "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_contains "title in response" "Smoke Test Series" "$GET_RESP"
POSTS_VAL=$(echo "$GET_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); posts=d.get('data',{}).get('posts',None); print('present' if posts is not None else 'absent')" 2>/dev/null || echo "absent")
if [ "$POSTS_VAL" = "present" ]; then
  echo "  ✓ posts field present in series response"
  PASS=$((PASS + 1))
else
  echo "  ✗ posts field missing from series response"
  FAIL=$((FAIL + 1))
fi

# ── Step 3 — Add post to series ───────────────────────────────────────────
if [ -n "$POST_ID" ]; then
  echo ""
  echo "Step 3 — POST /posts/${POST_ID}/series (series_ids=[${SERIES_ID}]) → expect 200"
  SERIES_BODY="{\"series_ids\":[\"${SERIES_ID}\"]}"
  SERIES_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${POST_ID}/series" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d "$SERIES_BODY")
  assert_status "update_post_series 200" "200" "$SERIES_HTTP"
  SERIES_RESP=$(curl -s -X POST "${API}/posts/${POST_ID}/series" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d "$SERIES_BODY")
  SERIES_COUNT=$(echo "$SERIES_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('series_count','?'))" 2>/dev/null || echo "?")
  if [ "$SERIES_COUNT" = "1" ]; then
    echo "  ✓ series_count: 1"
    PASS=$((PASS + 1))
  else
    echo "  ✗ series_count: expected 1, got '${SERIES_COUNT}'"
    FAIL=$((FAIL + 1))
  fi
else
  echo ""
  echo "Step 3 — SKIPPED (POST_ID not available)"
fi

# ── Step 4 — PATCH series (owner) ─────────────────────────────────────────
echo ""
echo "Step 4 — PATCH /series/${SERIES_ID} (title update, owner) → expect 200"
PATCH_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Smoke Title"}')
assert_status "patch_series 200" "200" "$PATCH_HTTP"
PATCH_RESP=$(curl -s -X PATCH "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Smoke Title 2"}')
assert_contains "updated title" "Updated Smoke Title" "$PATCH_RESP"

# ── Step 5 (optional) — PATCH from OTHER_TOKEN → 403 SERIES_NOT_OWNER ────
if [ -n "$OTHER_TOKEN" ]; then
  echo ""
  echo "Step 5 — PATCH /series/${SERIES_ID} from OTHER_TOKEN → expect 403 SERIES_NOT_OWNER"
  CROSS_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "${API}/series/${SERIES_ID}" \
    -H "Authorization: Bearer ${OTHER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"title":"Unauthorized Change"}')
  assert_status "cross-ownership 403" "403" "$CROSS_HTTP"
  CROSS_RESP=$(curl -s -X PATCH "${API}/series/${SERIES_ID}" \
    -H "Authorization: Bearer ${OTHER_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"title":"Unauthorized Change"}')
  assert_contains "SERIES_NOT_OWNER code" "SERIES_NOT_OWNER" "$CROSS_RESP"
else
  echo ""
  echo "Step 5 — SKIPPED (OTHER_TOKEN not set; set OTHER_TOKEN=eyJ... to enable cross-ownership check)"
fi

# ── Step 6 — DELETE series ─────────────────────────────────────────────────
echo ""
echo "Step 6 — DELETE /series/${SERIES_ID} → expect 204"
DEL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "delete_series 204" "204" "$DEL_HTTP"

# Verify the series is gone
GONE_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${API}/series/${SERIES_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "series gone after delete 404" "404" "$GONE_HTTP"

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
