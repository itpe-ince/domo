#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Smoke test — auction-promotion-suite (#11) PR2
# ─────────────────────────────────────────────────────────────────────────────
# Verifies:
#   1. Artist generates share card → 200 + share_card_url returned
#   2. Cache hit (immediate re-call) → cached=true
#   3. Non-owner → 403 FORBIDDEN   (requires OTHER_TOKEN)
#   4. Unauthenticated → 401/403
#
# Backend handler: api/auctions.py::create_share_card
# Design ref:      v1/docs/02-design/features/auction-promotion-suite.design.md §B-7, §B-13
#
# Usage:
#   ARTIST_TOKEN=eyJ... AUCTION_ID=<uuid> ./smoke_test_auction_promotion.sh
#
# Optional env:
#   BASE_URL     — base URL (default: http://localhost:8000)
#   OTHER_TOKEN  — bearer token for a non-owner account (optional, enables Step 3)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE="${BASE_URL:-http://localhost:8000}/v1"
ARTIST_TOKEN="${ARTIST_TOKEN:-}"
OTHER_TOKEN="${OTHER_TOKEN:-}"
AUCTION_ID="${AUCTION_ID:-}"

if [ -z "$ARTIST_TOKEN" ] || [ -z "$AUCTION_ID" ]; then
  echo "ERROR: ARTIST_TOKEN and AUCTION_ID are required."
  echo "Usage:"
  echo "  ARTIST_TOKEN=eyJ... AUCTION_ID=<uuid> ./smoke_test_auction_promotion.sh"
  exit 1
fi

PASS=0
FAIL=0

assert_status() {
  local label="$1" expected="$2" got="$3"
  if [ "$expected" = "$got" ]; then
    PASS=$((PASS + 1))
    echo "  PASS ${label} (${got})"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL ${label} (expected ${expected}, got ${got})"
  fi
}

# ── Step 1: artist generates share card → 200 ────────────────────────────────
echo ""
echo "Step 1 — POST /auctions/${AUCTION_ID}/share-card as artist → expect 200 + share_card_url"
HTTP1=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${ARTIST_TOKEN}" \
  "${BASE}/auctions/${AUCTION_ID}/share-card")
assert_status "Step 1 artist 200" "200" "$HTTP1"

if [ "$HTTP1" = "200" ]; then
  RESP1=$(curl -sf \
    -X POST \
    -H "Authorization: Bearer ${ARTIST_TOKEN}" \
    "${BASE}/auctions/${AUCTION_ID}/share-card")
  if echo "$RESP1" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['data']['share_card_url']" 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "  PASS Step 1 share_card_url present"
  else
    FAIL=$((FAIL + 1))
    echo "  FAIL Step 1 share_card_url missing in response"
    echo "  Response: ${RESP1}"
  fi
fi

# ── Step 2: cache hit (immediate re-call) → cached=true ──────────────────────
echo ""
echo "Step 2 — immediate re-call → expect cached=true"
RESP2=$(curl -sf \
  -X POST \
  -H "Authorization: Bearer ${ARTIST_TOKEN}" \
  "${BASE}/auctions/${AUCTION_ID}/share-card")
CACHED=$(echo "$RESP2" | python3 -c "import sys,json; print(str(json.load(sys.stdin)['data']['cached']).lower())" 2>/dev/null || echo "error")
if [ "$CACHED" = "true" ]; then
  PASS=$((PASS + 1))
  echo "  PASS Step 2 cached=true"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL Step 2 cached=${CACHED} (expected true)"
fi

# ── Step 3: non-owner → 403 (optional) ──────────────────────────────────────
echo ""
if [ -n "$OTHER_TOKEN" ]; then
  echo "Step 3 — non-owner call → expect 403"
  HTTP3=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${OTHER_TOKEN}" \
    "${BASE}/auctions/${AUCTION_ID}/share-card")
  assert_status "Step 3 non-owner 403" "403" "$HTTP3"
else
  echo "Step 3 — SKIPPED (OTHER_TOKEN not set)"
fi

# ── Step 4: unauthenticated → 401 or 403 ─────────────────────────────────────
echo ""
echo "Step 4 — unauthenticated → expect 401 or 403"
HTTP4=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST \
  "${BASE}/auctions/${AUCTION_ID}/share-card")
if [ "$HTTP4" = "401" ] || [ "$HTTP4" = "403" ]; then
  PASS=$((PASS + 1))
  echo "  PASS Step 4 non-auth blocked (${HTTP4})"
else
  FAIL=$((FAIL + 1))
  echo "  FAIL Step 4 expected 401/403, got ${HTTP4}"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
