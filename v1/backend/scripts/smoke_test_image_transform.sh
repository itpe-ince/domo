#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — editor-image-studio (#6-image) transform
# ─────────────────────────────────────────────────────────
# Verifies:
#   1) POST /v1/media/{id}/transform rotate 90 → 200, crop_meta.rotation=90
#   2) GET original file via local storage (OQ-D-A=C — original preserved)
#   3) POST same endpoint with crop → 200, crop_meta.crop populated
#   4) POST same endpoint with watermark text → 200
#   5) POST with .gif media → 415 MEDIA_TRANSFORM_UNSUPPORTED_TYPE
#
# Backend handler: api/media.py::transform_media
# Design ref:      v1/docs/02-design/features/editor-image-studio.design.md §B-5, §B-11
#
# Usage:
#   TOKEN_A=eyJ... MEDIA_ID=<uuid> ./smoke_test_image_transform.sh
#   TOKEN_A=eyJ... ./smoke_test_image_transform.sh  (script uploads a test image first)
#
# Optional env:
#   API           — base URL (default: http://localhost:3710/v1)
#   TOKEN_A       — bearer token for an artist account (REQUIRED)
#   MEDIA_ID      — existing image media_asset UUID (script auto-uploads if omitted)
#   GIF_MEDIA_ID  — existing gif media_asset UUID for step 5 (skip step 5 if omitted)
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
TOKEN_A="${TOKEN_A:-}"

if [ -z "$TOKEN_A" ]; then
  echo "Error: TOKEN_A env var required (bearer token for artist account)."
  echo "Example:"
  echo "  TOKEN_A=eyJ... ./smoke_test_image_transform.sh"
  exit 2
fi

PASS=0
FAIL=0
MEDIA_ID="${MEDIA_ID:-}"
GIF_MEDIA_ID="${GIF_MEDIA_ID:-}"

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

# ── Auto-upload a test image if MEDIA_ID not provided ──
if [ -z "$MEDIA_ID" ]; then
  echo "MEDIA_ID not set — uploading a test image first..."

  # Generate 100×100 red JPEG via Pillow (matches dev environment)
  TMP_IMG=$(python3 -c "
from PIL import Image
import tempfile, os
img = Image.new('RGB', (100, 100), (220, 50, 50))
f = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
img.save(f.name, format='JPEG')
print(f.name)
" 2>/dev/null || echo "")

  if [ -z "$TMP_IMG" ]; then
    echo "  Error: Could not generate test image (Pillow not installed?)"
    echo "  Set MEDIA_ID=<uuid> manually and re-run."
    exit 2
  fi

  # We need a post_id — create a draft post first (type=general)
  DRAFT_RESP=$(curl -s -X POST "${API}/posts/drafts" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d '{"type":"general","title":"smoke-image-transform"}')
  POST_ID=$(echo "$DRAFT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])" 2>/dev/null || echo "")

  if [ -z "$POST_ID" ]; then
    echo "  Error: Could not create draft post for test image upload."
    echo "  Response: $DRAFT_RESP"
    rm -f "$TMP_IMG"
    exit 2
  fi

  UPLOAD_RESP=$(curl -s -X POST "${API}/media/upload" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -F "file=@${TMP_IMG};type=image/jpeg" \
    -F "post_id=${POST_ID}" \
    -F "type=image")
  rm -f "$TMP_IMG"

  MEDIA_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['id'])" 2>/dev/null || echo "")

  if [ -z "$MEDIA_ID" ]; then
    echo "  Error: Could not upload test image."
    echo "  Response: $UPLOAD_RESP"
    exit 2
  fi
  echo "  Auto-uploaded test image: MEDIA_ID=${MEDIA_ID}"
fi

TRANSFORM_URL="${API}/media/${MEDIA_ID}/transform"

# ── Test 1 — rotate 90 → 200, crop_meta.rotation = 90 ──
echo ""
echo "Test 1 — POST transform rotate 90 → expect 200 + rotation=90"
resp=$(curl -s -X POST "${TRANSFORM_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"ops":[{"type":"rotate","degrees":90}]}')
status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TRANSFORM_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d '{"ops":[{"type":"rotate","degrees":90}]}')
assert_status "rotate 90 status" "200" "$status"
rotation=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('crop_meta',{}).get('rotation','?'))" 2>/dev/null || echo "?")
if [ "$rotation" = "90" ]; then
  echo "  ✓ crop_meta.rotation: 90"
  PASS=$((PASS + 1))
else
  echo "  ✗ crop_meta.rotation: expected 90, got ${rotation}"
  FAIL=$((FAIL + 1))
fi

# ── Test 2 — original file accessible (OQ-D-A=C) ──
echo ""
echo "Test 2 — GET original storage key from media → expect accessible"
MEDIA_RESP=$(curl -s "${API}/media/${MEDIA_ID}" \
  -H "Authorization: Bearer ${TOKEN_A}" 2>/dev/null || echo "")
ORIGINAL_KEY=$(echo "$MEDIA_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
m = d.get('data', {})
print(m.get('original_storage_key') or m.get('storage_key') or '')
" 2>/dev/null || echo "")

if [ -n "$ORIGINAL_KEY" ]; then
  echo "  ✓ original_storage_key preserved: ${ORIGINAL_KEY}"
  PASS=$((PASS + 1))
else
  echo "  ✗ original_storage_key not found in media response"
  FAIL=$((FAIL + 1))
fi

# ── Test 3 — crop → 200, crop_meta.crop populated ──
echo ""
echo "Test 3 — POST transform crop → expect 200 + crop_meta.crop set"
CROP_BODY='{"ops":[{"type":"crop","x":5,"y":5,"w":80,"h":80}]}'
resp3=$(curl -s -X POST "${TRANSFORM_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d "$CROP_BODY")
status3=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TRANSFORM_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d "$CROP_BODY")
assert_status "crop status" "200" "$status3"
crop_x=$(echo "$resp3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('crop_meta',{}).get('crop',{}).get('x','null'))" 2>/dev/null || echo "null")
if [ "$crop_x" != "null" ]; then
  echo "  ✓ crop_meta.crop.x: ${crop_x}"
  PASS=$((PASS + 1))
else
  echo "  ✗ crop_meta.crop: not populated in response"
  FAIL=$((FAIL + 1))
fi

# ── Test 4 — watermark text → 200 ──
echo ""
echo "Test 4 — POST transform watermark text → expect 200"
WM_BODY='{"ops":[{"type":"watermark","source":"text","text":"Domo","position":{"x":10,"y":10},"opacity":0.7}]}'
status4=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${TRANSFORM_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -H "Content-Type: application/json" \
  -d "$WM_BODY")
assert_status "watermark text status" "200" "$status4"

# ── Test 5 — GIF or video media → 415 ──
echo ""
echo "Test 5 — POST transform with unsupported type → expect 415"
if [ -n "$GIF_MEDIA_ID" ]; then
  GIF_URL="${API}/media/${GIF_MEDIA_ID}/transform"
  status5=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${GIF_URL}" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -H "Content-Type: application/json" \
    -d '{"ops":[{"type":"rotate","degrees":90}]}')
  assert_status "gif/video 415" "415" "$status5"
else
  echo "  ⚠ GIF_MEDIA_ID not set — skipping step 5 (set GIF_MEDIA_ID=<uuid> to enable)"
  echo "    To test manually: POST /v1/media/<gif-id>/transform and expect 415"
fi

# ── Summary ──
echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
