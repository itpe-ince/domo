#!/bin/bash
# i18n-key-audit.sh — CO-1 PR-5: 5 locale 키 매트릭스 비교
#
# 사용법:
#   bash scripts/i18n-key-audit.sh           # 프론트엔드 루트에서 실행
#   bash v1/frontend/scripts/i18n-key-audit.sh  # 레포 루트에서 실행
#
# 동작:
#   ko.json 기준 최상위 키 추출 → en/ja/zh/es 누락 키 검출
#   누락 발견 시 console.error + exit 1
#
# 의도적 locale 차이 예외 처리 (allowlist):
#   ALLOWLIST 배열에 키 이름을 추가하면 해당 키는 누락 검사에서 제외됨.
#   예: ALLOWLIST=("some_ko_only_key" "another_key")
#
# 의존성:
#   - jq (brew install jq / apt-get install jq)
#   - bash 3.2+

set -euo pipefail

# ─── 경로 설정 ───────────────────────────────────────────────────────────────
# 스크립트 위치를 기준으로 i18n 디렉토리 탐색
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
I18N_DIR="$(cd "${SCRIPT_DIR}/../src/i18n" && pwd)"

BASE="${I18N_DIR}/ko.json"
LOCALES=("en" "ja" "zh" "es")

# ─── Allowlist (의도적 locale 차이 예외 처리) ─────────────────────────────────
# 특정 키를 누락 검사에서 제외하려면 이 배열에 추가
# 예: ALLOWLIST=("some_feature_flag_key")
ALLOWLIST=()

# ─── jq 설치 확인 ────────────────────────────────────────────────────────────
if ! command -v jq &>/dev/null; then
  echo "[ERROR] jq가 설치되어 있지 않습니다."
  echo "  macOS:  brew install jq"
  echo "  Ubuntu: sudo apt-get install -y jq"
  exit 1
fi

# ─── 기준 파일 확인 ──────────────────────────────────────────────────────────
if [[ ! -f "$BASE" ]]; then
  echo "[ERROR] 기준 파일을 찾을 수 없습니다: ${BASE}"
  exit 1
fi

echo "[i18n-audit] 기준 파일: ${BASE}"
echo "[i18n-audit] 검사 locale: ${LOCALES[*]}"

# ─── 키 추출 함수 (최상위 + 1단계 중첩까지) ─────────────────────────────────
# ko.json 기준으로 최상위 키만 비교 (중첩 키는 추후 확장 가능)
get_top_level_keys() {
  local file="$1"
  jq -r 'keys[]' "$file" 2>/dev/null
}

get_nested_keys() {
  local file="$1"
  # 최상위 + 2단계 중첩 키를 "parent.child" 형식으로 추출
  jq -r '
    to_entries[] |
    .key as $top |
    if (.value | type) == "object" then
      .value | to_entries[] | "\($top).\(.key)"
    else
      $top
    end
  ' "$file" 2>/dev/null
}

# ─── 누락 키 검출 ────────────────────────────────────────────────────────────
FAILED=0
TOTAL_MISSING=0

for locale in "${LOCALES[@]}"; do
  TARGET="${I18N_DIR}/${locale}.json"

  if [[ ! -f "$TARGET" ]]; then
    echo "[FAIL] ${locale}.json 파일이 없습니다: ${TARGET}"
    FAILED=1
    continue
  fi

  # 최상위 키 비교
  BASE_KEYS=$(get_nested_keys "$BASE")
  TARGET_KEYS=$(get_nested_keys "$TARGET")

  MISSING_KEYS=()
  while IFS= read -r key; do
    # allowlist 확인
    skip=0
    for allowed in "${ALLOWLIST[@]}"; do
      if [[ "$key" == "$allowed" ]]; then
        skip=1
        break
      fi
    done
    [[ $skip -eq 1 ]] && continue

    # 누락 확인 (grep -qxF: 정확한 줄 일치)
    if ! echo "$TARGET_KEYS" | grep -qxF "$key"; then
      MISSING_KEYS+=("$key")
    fi
  done <<< "$BASE_KEYS"

  if [[ ${#MISSING_KEYS[@]} -gt 0 ]]; then
    echo "[FAIL] ${locale}.json 누락 키 (${#MISSING_KEYS[@]}건):"
    for key in "${MISSING_KEYS[@]}"; do
      echo "  - ${key}"
    done
    FAILED=1
    TOTAL_MISSING=$((TOTAL_MISSING + ${#MISSING_KEYS[@]}))
  else
    echo "[OK]   ${locale}.json — 누락 키 없음"
  fi
done

# ─── 결과 출력 ───────────────────────────────────────────────────────────────
echo ""
if [[ $FAILED -eq 0 ]]; then
  echo "[i18n-audit] 검사 완료: 5 locale 모두 키 일치"
  exit 0
else
  echo "[i18n-audit] 검사 실패: 누락 키 ${TOTAL_MISSING}건 발견"
  echo "  ko.json 기준으로 누락된 키를 해당 locale 파일에 추가해 주세요."
  exit 1
fi
