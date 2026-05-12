#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Smoke test — editor-image-studio (#6-image) signature
# ─────────────────────────────────────────────────────────
# Verifies:
#   Group 1 — Initial state: GET /v1/me/signature → signature_url null
#   Group 2 — Upload: POST /v1/me/signature (PNG) → 200, signature_url returned
#             GET /v1/me/signature → signature_url not null
#   Group 3 — Error + Delete: POST with image/jpeg → 415 SIGNATURE_UNSUPPORTED_TYPE
#             DELETE /v1/me/signature → 204
#             GET /v1/me/signature → signature_url null (cleared)
#
# Backend handler: api/me.py  (POST/GET/DELETE /v1/me/signature)
# Design ref:      v1/docs/02-design/features/editor-image-studio.design.md §B-14
#
# Usage:
#   TOKEN_A=eyJ... ./smoke_test_signature.sh
#   TOKEN_A=eyJ... SIGNATURE_PNG_PATH=/path/to/sig.png ./smoke_test_signature.sh
#
# Optional env:
#   API                  — base URL (default: http://localhost:3710/v1)
#   TOKEN_A              — bearer token for any account (REQUIRED)
#   SIGNATURE_PNG_PATH   — path to a PNG file to upload (auto-generated if omitted)
# ─────────────────────────────────────────────────────────
set -euo pipefail

API="${API:-http://localhost:3710/v1}"
TOKEN_A="${TOKEN_A:-}"

if [ -z "$TOKEN_A" ]; then
  echo "Error: TOKEN_A env var required."
  echo "Example:"
  echo "  TOKEN_A=eyJ... ./smoke_test_signature.sh"
  exit 2
fi

PASS=0
FAIL=0
SIG_URL="${API}/me/signature"
TMP_PNG=""

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

assert_null() {
  local label="$1" value="$2"
  if [ "$value" = "null" ] || [ "$value" = "None" ] || [ -z "$value" ]; then
    echo "  ✓ ${label}: null"
    PASS=$((PASS + 1))
  else
    echo "  ✗ ${label}: expected null, got '${value}'"
    FAIL=$((FAIL + 1))
  fi
}

assert_not_null() {
  local label="$1" value="$2"
  if [ -n "$value" ] && [ "$value" != "null" ] && [ "$value" != "None" ]; then
    echo "  ✓ ${label}: ${value}"
    PASS=$((PASS + 1))
  else
    echo "  ✗ ${label}: expected non-null, got '${value}'"
    FAIL=$((FAIL + 1))
  fi
}

# ── Prepare PNG ──
SIGNATURE_PNG_PATH="${SIGNATURE_PNG_PATH:-}"
if [ -z "$SIGNATURE_PNG_PATH" ]; then
  TMP_PNG=$(python3 -c "
from PIL import Image
import tempfile
img = Image.new('RGBA', (8, 8), (255, 0, 0, 255))
f = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
img.save(f.name, format='PNG')
print(f.name)
" 2>/dev/null || echo "")

  if [ -z "$TMP_PNG" ]; then
    echo "Error: Could not generate test PNG (Pillow not installed?)."
    echo "Set SIGNATURE_PNG_PATH=/path/to/sig.png and re-run."
    exit 2
  fi
  SIGNATURE_PNG_PATH="$TMP_PNG"
  echo "  Generated test PNG: ${SIGNATURE_PNG_PATH}"
fi

cleanup() {
  [ -n "$TMP_PNG" ] && rm -f "$TMP_PNG"
}
trap cleanup EXIT

# ── Group 1 — Initial state ──
echo ""
echo "Test 1 — GET /v1/me/signature → expect 200, signature_url null"
resp1=$(curl -s "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
status1=$(curl -s -o /dev/null -w "%{http_code}" "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "GET signature initial status" "200" "$status1"
sig_url_1=$(echo "$resp1" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('signature_url'))" 2>/dev/null || echo "")
assert_null "signature_url initially null" "$sig_url_1"

# ── Group 2 — Upload PNG ──
echo ""
echo "Test 2 — POST /v1/me/signature with PNG → expect 200, signature_url returned"
resp2=$(curl -s -X POST "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -F "file=@${SIGNATURE_PNG_PATH};type=image/png")
status2=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}" \
  -F "file=@${SIGNATURE_PNG_PATH};type=image/png")
assert_status "POST signature PNG status" "200" "$status2"
sig_url_2=$(echo "$resp2" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('signature_url') or '')" 2>/dev/null || echo "")
assert_not_null "signature_url returned after upload" "$sig_url_2"

echo ""
echo "Test 3 — GET /v1/me/signature after upload → expect signature_url not null"
resp3=$(curl -s "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
status3=$(curl -s -o /dev/null -w "%{http_code}" "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "GET after upload status" "200" "$status3"
sig_url_3=$(echo "$resp3" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('signature_url') or '')" 2>/dev/null || echo "")
assert_not_null "signature_url not null after upload" "$sig_url_3"

# ── Group 3 — Error + Delete ──
echo ""
echo "Test 4 — POST /v1/me/signature with image/jpeg → expect 415"
# Create a minimal JPEG for the wrong-type test
TMP_JPEG=$(python3 -c "
from PIL import Image
import tempfile
img = Image.new('RGB', (4, 4), (255, 0, 0))
f = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
img.save(f.name, format='JPEG')
print(f.name)
" 2>/dev/null || echo "")

if [ -n "$TMP_JPEG" ]; then
  status4=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${SIG_URL}" \
    -H "Authorization: Bearer ${TOKEN_A}" \
    -F "file=@${TMP_JPEG};type=image/jpeg")
  rm -f "$TMP_JPEG"
  assert_status "POST signature JPEG → 415" "415" "$status4"
else
  echo "  ⚠ Could not generate JPEG for type-error test (Pillow issue) — skipping"
fi

echo ""
echo "Test 5 — DELETE /v1/me/signature → expect 204, then GET → null"
status5=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
assert_status "DELETE signature status" "204" "$status5"

resp5g=$(curl -s "${SIG_URL}" \
  -H "Authorization: Bearer ${TOKEN_A}")
sig_url_5=$(echo "$resp5g" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('signature_url'))" 2>/dev/null || echo "")
assert_null "signature_url null after delete" "$sig_url_5"

# ── Summary ──
echo ""
echo "─────────────────────────────────────"
echo "Result: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
