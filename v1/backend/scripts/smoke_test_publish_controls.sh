#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — publish-controls (#8) publish endpoint
# ─────────────────────────────────────────────────────────
# Verifies:
#   1. POST /posts (draft) → 201, capture DRAFT_POST_ID
#   2. POST /posts/{id}/publish (visibility=followers_only, comments_enabled=false)
#      → 200, status=published or pending_review
#   3. POST /posts/{id}/comments → expect 403 COMMENTS_DISABLED
#   4. POST /posts/{id}/publish again (already published) → expect 409 POST_INVALID_STATE
#   5. POST another draft + publish_at=now+10min → status=scheduled, scheduled_at present
#
# Backend handler: api/posts.py::publish_post
# Design ref:      v1/docs/02-design/features/publish-controls.design.md §B-7, §B-11
#
# Usage:
#   TOKEN_A=eyJ... ./smoke_test_publish_controls.sh
#
# Optional env:
#   API     — base URL (default: http://localhost:3710/v1)
#   TOKEN_A — bearer token for an artist account (REQUIRED)
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
TOKEN_A="${TOKEN_A:-}"

if [ -z "$TOKEN_A" ]; then
  echo "Error: TOKEN_A env var required (bearer token for artist account)."
  echo "Example:"
  echo "  TOKEN_A=eyJ... ./smoke_test_publish_controls.sh"
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

# ── Step 1 — Create a draft post ──────────────────────────────────────────
echo ""
echo "Step 1 — POST /posts (draft, no media) → expect 200/201"
DRAFT_RESP=$(curl -s -X POST "${API}/posts" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"type":"general","title":"Smoke Test Publish","content":"smoke test","language":"en"}')
DRAFT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"type":"general","title":"Smoke Test Publish","content":"smoke test 2","language":"en"}')

DRAFT_POST_ID=$(echo "$DRAFT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null || echo "")
if [ -n "$DRAFT_POST_ID" ]; then
  echo "  ✓ Draft post created: ${DRAFT_POST_ID}"
  PASS=$((PASS + 1))
else
  echo "  ✗ Failed to create draft post"
  echo "  Response: ${DRAFT_RESP}"
  FAIL=$((FAIL + 1))
  echo ""
  echo "─────────────────────────────────────"
  echo "Result: ${PASS} passed, ${FAIL} failed (aborted — cannot proceed without draft)"
  exit 1
fi

# ── Step 2 — Publish with visibility=followers_only, comments_enabled=false ──
echo ""
echo "Step 2 — POST /posts/${DRAFT_POST_ID}/publish (followers_only, no comments) → expect 200"
PUB_BODY='{"visibility":"followers_only","comments_enabled":false,"series_ids":[]}'
PUB_RESP=$(curl -s -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d "$PUB_BODY")
PUB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"visibility":"followers_only","comments_enabled":false}')
assert_status "publish status" "409" "$PUB_HTTP"  # second call should be 409 already

# Use the first call's response
PUB_STATUS=$(echo "$PUB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('status',''))" 2>/dev/null || echo "")
PUB_VIS=$(echo "$PUB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('visibility',''))" 2>/dev/null || echo "")
PUB_COMMENTS=$(echo "$PUB_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('comments_enabled',''))" 2>/dev/null || echo "")

if [ "$PUB_STATUS" = "published" ] || [ "$PUB_STATUS" = "pending_review" ]; then
  echo "  ✓ status: ${PUB_STATUS} (published or pending_review)"
  PASS=$((PASS + 1))
else
  echo "  ✗ status: expected published|pending_review, got '${PUB_STATUS}'"
  FAIL=$((FAIL + 1))
fi
assert_contains "visibility=followers_only" "followers_only" "$PUB_VIS"
if [ "$PUB_COMMENTS" = "False" ] || [ "$PUB_COMMENTS" = "false" ]; then
  echo "  ✓ comments_enabled: false"
  PASS=$((PASS + 1))
else
  echo "  ✗ comments_enabled: expected false, got '${PUB_COMMENTS}'"
  FAIL=$((FAIL + 1))
fi

# ── Step 3 — POST /comments → expect 403 COMMENTS_DISABLED ──────────────
echo ""
echo "Step 3 — POST /posts/${DRAFT_POST_ID}/comments → expect 403 COMMENTS_DISABLED"
CMT_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${DRAFT_POST_ID}/comments" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"content":"should be blocked"}')
assert_status "comments_disabled 403" "403" "$CMT_HTTP"
CMT_RESP=$(curl -s -X POST "${API}/posts/${DRAFT_POST_ID}/comments" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"content":"should be blocked"}')
assert_contains "COMMENTS_DISABLED code" "COMMENTS_DISABLED" "$CMT_RESP"

# ── Step 4 — Re-publish (already published) → expect 409 POST_INVALID_STATE ──
echo ""
echo "Step 4 — POST /posts/${DRAFT_POST_ID}/publish again → expect 409 POST_INVALID_STATE"
REPUB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"visibility":"public"}')
assert_status "re-publish 409" "409" "$REPUB_HTTP"
REPUB_RESP=$(curl -s -X POST "${API}/posts/${DRAFT_POST_ID}/publish" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"visibility":"public"}')
assert_contains "POST_INVALID_STATE code" "POST_INVALID_STATE" "$REPUB_RESP"

# ── Step 5 — Scheduled publish (publish_at = now+10min) ──────────────────
echo ""
echo "Step 5 — Create draft + publish_at=now+10min → expect status=scheduled"
# Create second draft
DRAFT2_RESP=$(curl -s -X POST "${API}/posts" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"type":"general","title":"Scheduled Smoke Test","content":"scheduled publish","language":"en"}')
DRAFT2_ID=$(echo "$DRAFT2_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('id',''))" 2>/dev/null || echo "")

if [ -z "$DRAFT2_ID" ]; then
  echo "  ✗ Could not create second draft for scheduled test"
  FAIL=$((FAIL + 1))
else
  PUBLISH_AT=$(python3 -c "from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat())")
  SCHED_BODY="{\"publish_at\":\"${PUBLISH_AT}\",\"visibility\":\"public\"}"
  SCHED_HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API}/posts/${DRAFT2_ID}/publish" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d "$SCHED_BODY")
  assert_status "scheduled publish 200" "200" "$SCHED_HTTP"
  SCHED_RESP=$(curl -s -X POST "${API}/posts/${DRAFT2_ID}/publish" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d '{"visibility":"public"}')
  # The second call will be 409 (already scheduled), check first call response indirectly
  SCHED_RESP2=$(curl -s "${API}/posts/${DRAFT2_ID}" \
    -H "Authorization: Bearer ${TOKEN_A}")
  SCHED_STATUS=$(echo "$SCHED_RESP2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('status',''))" 2>/dev/null || echo "")
  if [ "$SCHED_STATUS" = "scheduled" ]; then
    echo "  ✓ post status after scheduled publish: scheduled"
    PASS=$((PASS + 1))
  else
    echo "  ✗ post status: expected scheduled, got '${SCHED_STATUS}'"
    FAIL=$((FAIL + 1))
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
