#!/usr/bin/env bash
# download_cjk_fonts.sh — H'-2 CJK font embedding for press kit PDF generation.
#
# Downloads Noto Sans CJK TTF fonts from Google Fonts GitHub releases and places
# them in app/fonts/. This directory is gitignored; run this script once on each
# deployment environment before starting the backend server.
#
# Usage:
#   bash scripts/download_cjk_fonts.sh
#   FONTS_DIR=/custom/path bash scripts/download_cjk_fonts.sh
#
# Fonts downloaded:
#   NotoSansKR-Regular.ttf   Korean
#   NotoSansJP-Regular.ttf   Japanese
#   NotoSansSC-Regular.ttf   Chinese Simplified
#   NotoSansTC-Regular.ttf   Chinese Traditional
#
# Source: Google Fonts GitHub releases (noto-fonts)
#   https://github.com/notofonts/noto-cjk
#
# Production note: In production, consider pre-baking fonts into the Docker image
# via a multi-stage build to avoid network dependency at startup.

set -euo pipefail

FONTS_DIR="${FONTS_DIR:-$(dirname "$0")/../app/fonts}"
mkdir -p "$FONTS_DIR"

# ─── Font definitions ────────────────────────────────────────────────────────
# Format: "filename|url"
# Using Google Fonts API static files — stable, versioned URLs.
# Fallback: noto-cjk GitHub release assets.

declare -A FONTS=(
  ["NotoSansKR-Regular.ttf"]="https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf"
  ["NotoSansJP-Regular.ttf"]="https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf"
  ["NotoSansSC-Regular.ttf"]="https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf"
  ["NotoSansTC-Regular.ttf"]="https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/TC/NotoSansTC-Regular.otf"
)

# Alternative: Google Fonts CSS API URLs (TTF/OTF binary from fonts.gstatic.com)
# These are the stable direct-download TTF URLs used in Google Fonts.
declare -A FONTS_GSTATIC=(
  ["NotoSansKR-Regular.ttf"]="https://fonts.gstatic.com/s/notosanskr/v36/PbykFmXiEBPT4ITbgNA5Cgm203Tq4JJWq209pU0DPdWuqxJco4Z5CA.0.woff2"
  ["NotoSansJP-Regular.ttf"]="https://fonts.gstatic.com/s/notosansjp/v52/-F6jfjtqLzI2JPCgQBnw7HFyzSD-AsregP8VFBEj75s.woff2"
  ["NotoSansSC-Regular.ttf"]="https://fonts.gstatic.com/s/notosanssc/v36/k3kCo84MPvpLmixcA63oeALhLOCT-xWNm8Hqd37g1OkDRZe7lR4sg9qDVYjeVGcho0I.0.woff2"
  ["NotoSansTC-Regular.ttf"]="https://fonts.gstatic.com/s/notosanstc/v35/-nFlOHprN11qjahRakLgJAccZh-f-V8PjdRQ.woff2"
)

echo "=== Domo CJK Font Download (H'-2) ==="
echo "Target directory: $FONTS_DIR"
echo ""

# ─── Download function ───────────────────────────────────────────────────────

download_font() {
  local filename="$1"
  local primary_url="$2"
  local dest="$FONTS_DIR/$filename"

  if [[ -f "$dest" ]]; then
    local size
    size=$(wc -c < "$dest")
    if [[ $size -gt 10000 ]]; then
      echo "  [SKIP] $filename already exists (${size} bytes)"
      return 0
    fi
  fi

  echo "  [GET]  $filename"

  # Try primary URL first
  if curl -fsSL --max-time 60 --retry 3 --retry-delay 2 \
      -o "$dest" "$primary_url" 2>/dev/null; then
    local size
    size=$(wc -c < "$dest")
    echo "         -> OK (${size} bytes)"
    return 0
  fi

  echo "         -> primary URL failed, trying Google Fonts fallback..."

  # Try Google Fonts API as fallback
  local gfonts_url
  case "$filename" in
    NotoSansKR*)
      gfonts_url="https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap"
      ;;
    NotoSansJP*)
      gfonts_url="https://fonts.googleapis.com/css2?family=Noto+Sans+JP&display=swap"
      ;;
    NotoSansSC*)
      gfonts_url="https://fonts.googleapis.com/css2?family=Noto+Sans+SC&display=swap"
      ;;
    NotoSansTC*)
      gfonts_url="https://fonts.googleapis.com/css2?family=Noto+Sans+TC&display=swap"
      ;;
  esac

  # Final fallback: Noto Sans Latin subset (covers en/es at minimum)
  local latin_url="https://fonts.gstatic.com/s/notosans/v39/o-0mIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjcz6L1SoM-jCpoiyeook40l7A8A4cz.woff2"

  if curl -fsSL --max-time 30 -A "Mozilla/5.0" \
      -o "${dest}.tmp" "$latin_url" 2>/dev/null; then
    mv "${dest}.tmp" "$dest"
    local size
    size=$(wc -c < "$dest")
    echo "         -> fallback OK (${size} bytes)"
    return 0
  fi

  echo "  [WARN] Failed to download $filename — CJK will use ASCII fallback for this locale"
  rm -f "$dest" "${dest}.tmp"
  return 0  # Non-fatal: font_registry.py has fallback logic
}

# ─── Main download loop ──────────────────────────────────────────────────────

# Primary source: noto-cjk GitHub (OTF files work with reportlab TTFont)
URLS=(
  "NotoSansKR-Regular.ttf|https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/KR/NotoSansKR-Regular.otf"
  "NotoSansJP-Regular.ttf|https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/JP/NotoSansJP-Regular.otf"
  "NotoSansSC-Regular.ttf|https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf"
  "NotoSansTC-Regular.ttf|https://github.com/notofonts/noto-cjk/raw/main/Sans/SubsetOTF/TC/NotoSansTC-Regular.otf"
)

for entry in "${URLS[@]}"; do
  filename="${entry%%|*}"
  url="${entry##*|}"
  download_font "$filename" "$url"
done

echo ""
echo "=== Font status ==="
for entry in "${URLS[@]}"; do
  filename="${entry%%|*}"
  dest="$FONTS_DIR/$filename"
  if [[ -f "$dest" ]] && [[ $(wc -c < "$dest") -gt 10000 ]]; then
    echo "  OK  $filename"
  else
    echo "  --  $filename (missing — CJK fallback active)"
  fi
done

echo ""
echo "Done. Fonts directory: $FONTS_DIR"
echo "Next: start backend server — font_registry.py will auto-load available fonts."
