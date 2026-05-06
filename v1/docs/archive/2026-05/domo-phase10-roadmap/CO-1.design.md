---
template: design
version: 1.0
feature: phase10-CO-1
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_plan: domo-phase10-roadmap.plan.md
status: Draft
---

# Phase 10 CO-1 — Phase 9 Carry-over 11항목 일괄 청산

> **목표**: K Wave 1 Gap Analysis(§5)에서 식별된 11개 잔존 항목을 6개 atomic PR로 청산.
> alembic 신규 없음. 기존 581 passed 유지 + 신규 테스트 추가.
> Wave A(K-8/K-2)와 병행 시작 가능. 각 PR 독립 머지 가능.

---

## 1. 목표 & Acceptance Criteria

### 목표

- 11개 carry-over 항목 전체 청산 (누락 0건)
- 6 sub-PR 독립 머지 가능 (PR 간 의존성 없음)
- 회귀 0건 — 기존 581 passed 유지
- tsc 0 errors (PR-4 이후)
- CI i18n 검증 자동화 (PR-5 이후 모든 PR에서 자동 실행)

### 11항목 → 6 PR 매핑

| # | 항목 | 출처 | PR |
|:-:|------|:----:|:--:|
| 1 | L-D 잔존 3 skipped tests 사유 명시 | K-wave1 §5 #11 | PR-1 |
| 2 | K-3 rate limit 3회/일/포스트 명시 코드 | K-wave1 §5 #7 | PR-2 |
| 3 | FeedItem/GalleryView 등 `<img>` alt sweep | K-wave1 §5 #8 | PR-2 |
| 4 | K-3 caption_override 단위 테스트 추가 | CO-1 신규 | PR-2 |
| 5 | K-5 작가 편집 페이지 도슨트 폼 | K-wave1 §5 #9 | PR-3 |
| 6 | K-5 작가 편집 페이지 도슨트 opt-out 토글 UI | K-wave1 §5 #9 | PR-3 |
| 7 | DocentSection 별도 컴포넌트 분리 | K-wave1 §1.3 deviation | PR-3 |
| 8 | FeedAlgo TypeScript 타입에 "v2" 추가 | K-wave1 §5 #6 | PR-4 |
| 9 | i18n 키 자동 검증 CI 도입 | K-wave1 §5 #10 | PR-5 |
| 10 | K-2 i18n 키 검증 통합 | CO-1 신규 | PR-5 |
| 11 | ml_experiments 보존 정책 문서화 + 운영 가이드 | CO-1 신규 | PR-6 |

---

## 2. 6 sub-PR 상세

### PR-1: 테스트 부채 청산 (TESTING_NOTES.md)

**변경 파일**

- `v1/backend/docs/TESTING_NOTES.md` — 신규 작성

**핵심 변경 내용**

- L-D 잔존 3 skipped tests 사유 명시:
  - `test_personalized_feed.py:87` — Phase 6 carry-over. real DB integration test, 현재 mock 환경에서 실행 불가. 진입 조건: CI에 실제 PostgreSQL + pgvector 환경 구성 시 (Phase 11+ 대상)
  - `test_fcm_push` (또는 동명 테스트) — FCM/APNs real token 필요. 외부 인프라 의존. 진입 조건: staging 환경에서 실제 FCM 자격증명 주입 시
  - `test_s3_upload` (또는 동명 테스트) — S3 boto3 stub 완료 전 skip. 진입 조건: boto3 LocalStack 또는 실 S3 설정 시
- 각 항목: skip 사유 / 해제 조건 / Phase 이월 시점 명시
- 과도한 mocking 금지 원칙 + 후속 테스트 정책 명시

**검증 명령**

```bash
# PR-1 검증
cat v1/backend/docs/TESTING_NOTES.md
grep -n "skip" v1/backend/tests/ -r | grep -v ".pyc"
```

**예상 작업 시간**: 15분

---

### PR-2: K-3 보강 (rate limit + alt sweep + 단위 테스트)

**변경 파일**

- `v1/backend/app/api/posts.py` — rate limit dep 추가 (regenerate_post_caption, update_caption_override)
- `v1/backend/app/core/rate_limit.py` — 'post_caption_regenerate' / 'post_caption_override' key 추가
- `v1/frontend/src/components/FeedItem.tsx` — `<img>` alt 속성 추가
- `v1/frontend/src/components/GalleryView.tsx` — `<img>` alt 속성 추가
- 기타 `<img>` 컴포넌트 (grep 결과에 따라 추가)
- `v1/backend/tests/unit/test_post_caption_override.py` — 신규

**핵심 변경 내용**

rate limit (백엔드):
- `rate_limit.py`: `post_caption_regenerate` = 3회/일/포스트 (Redis key: `rl:caption_regen:{user_id}:{post_id}`)
- `rate_limit.py`: `post_caption_override` = 10회/일/포스트
- `posts.py` `regenerate_post_caption()`: `Depends(rate_limit("post_caption_regenerate"))` 추가
- `posts.py` `update_caption_override()`: `Depends(rate_limit("post_caption_override"))` 추가

`<img>` alt sweep (프론트엔드):
- `FeedItem.tsx`: `<img alt={post.effective_caption || post.title || ""} />`
- `GalleryView.tsx`: 동일 패턴
- grep 대상: `src/components/` 전체 `<img` 태그 → alt 누락 일괄 수정

단위 테스트:
- `test_post_caption_override.py`:
  - `test_caption_override_max_length_500`: 500자 초과 → 422 Validation Error
  - `test_caption_override_empty_string`: 빈 문자열 허용 확인
  - `test_caption_regenerate_rate_limit_3_per_day`: 4회 요청 → 429 응답
  - `test_caption_override_rate_limit`: override 10회 초과 → 429

**검증 명령**

```bash
# 백엔드
cd v1/backend
pytest tests/unit/test_post_caption_override.py -v
pytest tests/ -v --tb=short 2>&1 | tail -5

# 프론트엔드 alt 확인
grep -rn "<img" v1/frontend/src/components/ | grep -v "alt="

# 빌드
cd v1/frontend && npm run build
```

**예상 작업 시간**: 90분

---

### PR-3: K-5 작가 콘솔 보강 (DocentSection 분리 + 편집 UI)

**변경 파일**

- `v1/frontend/src/components/DocentSection.tsx` — 신규 (기존 inline 추출)
- `v1/frontend/src/app/posts/[id]/page.tsx` — DocentSection import 변경 (inline 제거)
- `v1/frontend/src/app/posts/[id]/edit/page.tsx` — 도슨트 폼 + opt-out 토글 UI 추가 (또는 신규 생성)
- `v1/frontend/src/i18n/ko.json` — `docent.edit_page.*` 키 추가
- `v1/frontend/src/i18n/en.json` — 동일
- `v1/frontend/src/i18n/ja.json` — 동일
- `v1/frontend/src/i18n/zh.json` — 동일
- `v1/frontend/src/i18n/es.json` — 동일

**핵심 변경 내용**

DocentSection 분리:
- `DocentSection.tsx`: `/posts/[id]/page.tsx` L120~211 inline 컴포넌트 추출
- Props: `{ post, locale, isArtist }` 인터페이스 정의
- `/posts/[id]/page.tsx`에서 `import DocentSection from "@/components/DocentSection"` 으로 교체

작가 편집 페이지 도슨트 폼:
- `/posts/[id]/edit` 페이지에 "도슨트" 탭 또는 섹션 추가
- `artist_docent_text` textarea (PATCH `/posts/{id}/docent` 연결)
- "AI 도슨트 생성" 버튼 (POST `/posts/{id}/docent/generate` 호출)
- opt-out 토글 (PATCH `/posts/{id}/docent/opt-out` 연결)
- 로딩/에러 상태 처리

i18n 추가 키 (~5개):

| 키 | ko | en |
|----|----|----|
| `docent.edit_page.section_title` | "도슨트 편집" | "Edit Docent" |
| `docent.edit_page.manual_label` | "직접 작성" | "Write manually" |
| `docent.edit_page.generate_button` | "AI 도슨트 생성" | "Generate AI Docent" |
| `docent.edit_page.opt_out_toggle` | "AI 도슨트 비활성화" | "Disable AI Docent" |
| `docent.edit_page.save_success` | "저장되었습니다" | "Saved" |

**검증 명령**

```bash
# 프론트엔드 빌드 (tsc 포함)
cd v1/frontend && npm run build

# DocentSection import 확인
grep -n "DocentSection" v1/frontend/src/app/posts/\[id\]/page.tsx

# inline 컴포넌트 제거 확인 (120~211 라인 주변)
grep -n "artist_docent_text\|opted_out\|DocentSection" v1/frontend/src/app/posts/\[id\]/page.tsx
```

**예상 작업 시간**: 120분

---

### PR-4: TypeScript 타입 보강 (FeedAlgo "v2")

**변경 파일**

- `v1/frontend/src/lib/api.ts` — FeedAlgo 타입 확장

**핵심 변경 내용**

```typescript
// 변경 전
type FeedAlgo = "default" | "v1" | "auto";

// 변경 후
type FeedAlgo = "default" | "v1" | "v2" | "auto";
```

- K-8 Feature Flag 분기에서 `algo="v2"` 사용 시 타입 안전성 확보
- `getFeed(algo: FeedAlgo)` 등 관련 함수 시그니처 업데이트 (필요 시)
- tsc 0 errors 확인

**검증 명령**

```bash
cd v1/frontend
npx tsc --noEmit
npm run build

# 타입 확인
grep -n "FeedAlgo\|algo=" src/lib/api.ts
```

**예상 작업 시간**: 20분

---

### PR-5: i18n CI 자동 검증 도입

**변경 파일**

- `v1/frontend/scripts/i18n-key-audit.sh` — 신규 (jq 기반, GitHub Actions 내장 의존성 없음)
- `v1/frontend/package.json` — `lint:i18n` 스크립트 추가
- `.github/workflows/i18n-check.yml` — 신규 (또는 기존 CI에 step 추가)

**핵심 변경 내용**

`i18n-key-audit.sh` 구조:
```bash
#!/bin/bash
# ko.json 기준 키 추출 → en/ja/zh/es 누락 키 검출
BASE="v1/frontend/src/i18n/ko.json"
LOCALES="en ja zh es"
FAILED=0

for locale in $LOCALES; do
  TARGET="v1/frontend/src/i18n/${locale}.json"
  MISSING=$(jq --slurpfile base "$BASE" --slurpfile target "$TARGET" \
    -n '($base[0] | keys) - ($target[0] | keys) | .[]')
  if [ -n "$MISSING" ]; then
    echo "[FAIL] ${locale}.json missing keys: $MISSING"
    FAILED=1
  fi
done

exit $FAILED
```

`package.json`:
```json
"scripts": {
  "lint:i18n": "bash scripts/i18n-key-audit.sh"
}
```

GitHub Actions `i18n-check.yml`:
```yaml
on: [pull_request]
jobs:
  i18n-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash v1/frontend/scripts/i18n-key-audit.sh
```

- K-2 신규 키 `feed.discovery_badge` 포함 5 locale 검증
- 허용 목록(allowlist) 기반 의도적 locale 차이 예외 처리 지원 (주석으로 명시)

**검증 명령**

```bash
# 스크립트 직접 실행
bash v1/frontend/scripts/i18n-key-audit.sh

# package.json 스크립트 실행
cd v1/frontend && npm run lint:i18n

# 누락 키 시뮬레이션 (테스트용 임시 삭제 후 검증)
```

**예상 작업 시간**: 60분

---

### PR-6: 운영 정책 문서화

**변경 파일**

- `v1/docs/operations.md` — 신규 (또는 기존 observability.md 확장)
- `v1/backend/docs/TESTING_NOTES.md` — ml_experiments 보존 정책 섹션 추가 (PR-1 이후)

**핵심 변경 내용**

`operations.md` 주요 섹션:

1. **ml_experiments 보존 정책**
   - 실험 종료 후 90일간 보존 (통계 분석 충분 기간)
   - 90일 후: 집계 통계 요약 후 원본 레코드 삭제 또는 cold storage 이동
   - Phase 11에서 scheduled cleanup cron 구현 예정
   - 수동 삭제 명령:
     ```sql
     DELETE FROM ml_experiment_assignments
     WHERE experiment_id IN (
       SELECT experiment_id FROM ml_experiments
       WHERE status = 'completed' AND ended_at < NOW() - INTERVAL '90 days'
     );
     ```

2. **K-8 A/B 테스트 종료 절차**
   - 통계적 유의성 p < 0.05 달성 또는 14일 경과 후 결정
   - PostHog Experiment 종료 → `ml_experiments.status = 'completed'` 업데이트
   - 결과 요약 기록 (`ml_experiments.ended_at` 명시)

3. **K-1/K-3/K-5 운영 14일 후 KPI 측정 명령**

```bash
# K-1: ML 피드 interaction 누적 확인
psql $DATABASE_URL -c "
  SELECT COUNT(*) as total,
         COUNT(DISTINCT user_id) as unique_users,
         COUNT(DISTINCT post_id) as unique_posts
  FROM user_post_interactions
  WHERE created_at > NOW() - INTERVAL '14 days';"

# K-3: AI 캡션 생성률
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE ai_caption IS NOT NULL) as captioned,
    COUNT(*) FILTER (WHERE ai_caption IS NULL) as pending,
    COUNT(*) as total
  FROM posts WHERE media_type = 'image';"

# K-5: 도슨트 생성률 + opt-out 비율
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) FILTER (WHERE ai_docent_text IS NOT NULL) as with_docent,
    COUNT(*) FILTER (WHERE opted_out = true) as opted_out,
    COUNT(*) as total
  FROM posts;"
```

4. **ml_experiments 테이블 상태 확인**

```bash
psql $DATABASE_URL -c "
  SELECT experiment_id, name, status, started_at, ended_at,
         (SELECT COUNT(*) FROM ml_experiment_assignments a WHERE a.experiment_id = e.experiment_id) as assignments
  FROM ml_experiments e ORDER BY started_at DESC;"
```

**검증 명령**

```bash
# 파일 존재 확인
ls -la v1/docs/operations.md v1/backend/docs/TESTING_NOTES.md

# 정책 섹션 확인
grep -n "90일\|90 days\|ml_experiments" v1/docs/operations.md
```

**예상 작업 시간**: 45분

---

## 3. 우선순위 & 진입 순서

```
PR-1 (15분, 문서만) → PR-4 (20분, 단일 타입) → PR-2 (90분, alt+ratelimit+test)
  → PR-3 (120분, frontend UI) → PR-5 (60분, CI) → PR-6 (45분, 문서)
```

총 예상 작업 시간: ~6시간 (6 PR 순차 기준)

**PR 간 의존성 없음** — 각 PR 독립 머지 가능. PR-5 머지 이후 모든 후속 PR에서 i18n CI 자동 실행.

| 순서 | PR | 이유 |
|:----:|:--:|------|
| 1 | PR-1 | 가장 빠름. 문서 작성만. 이후 PR의 신규 테스트 정책 기준 제공 |
| 2 | PR-4 | 단일 파일 타입 변경. 빠른 tsc 검증 |
| 3 | PR-2 | backend + frontend 혼합. alt sweep 범위 확인 필요 |
| 4 | PR-3 | 가장 복잡한 frontend UI. PR-2 alt 패턴 참조 |
| 5 | PR-5 | CI 자동화. 이후 PR은 자동 검증 혜택 |
| 6 | PR-6 | 문서. ml_experiments 운영 정책 최종 확정 |

---

## 4. Test Plan

### 전체 회귀 검증 (모든 PR 후)

```bash
# 백엔드
cd v1/backend
pytest tests/ -v --tb=short 2>&1 | tail -10
# 목표: 581+ passed, 0 failed, skipped 유지

# 프론트엔드
cd v1/frontend
npm run build
# 목표: tsc 0 errors, 빌드 성공
```

### PR별 추가 검증

| PR | 추가 테스트 |
|:--:|------------|
| PR-2 | `tests/unit/test_post_caption_override.py` 신규 4건 |
| PR-3 | E2E 스모크: 작가 편집 페이지 도슨트 폼 + opt-out 토글 동작 |
| PR-4 | `npx tsc --noEmit` 0 errors |
| PR-5 | `npm run lint:i18n` 0 누락 키 |

### 신규 테스트 목록

`v1/backend/tests/unit/test_post_caption_override.py`:
- `test_caption_override_max_length_500`
- `test_caption_override_empty_string`
- `test_caption_regenerate_rate_limit_3_per_day`
- `test_caption_override_rate_limit`

예상 결과: 581 passed → 585+ passed (신규 4건 이상)

---

## 5. 위임 Agent

| PR | Agent | 주요 작업 |
|:--:|:-----:|----------|
| PR-1 | bkend-expert | TESTING_NOTES.md 작성. skip 사유 3건 명시 |
| PR-2 (backend) | bkend-expert | rate_limit.py 키 추가, posts.py dep 주입, test_post_caption_override.py 신규 |
| PR-2 (frontend) | frontend-architect | FeedItem/GalleryView alt sweep, 기타 `<img>` grep + 일괄 수정 |
| PR-3 | frontend-architect | DocentSection.tsx 분리, 편집 페이지 UI, i18n 5 locale 추가 |
| PR-4 | frontend-architect | api.ts FeedAlgo 타입 확장, tsc 검증 |
| PR-5 | frontend-architect | i18n-key-audit.sh 작성, GitHub Actions workflow, package.json 스크립트 |
| PR-6 | bkend-expert | operations.md 신규, TESTING_NOTES.md ml_experiments 섹션 추가 |

---

## 6. 주요 Risks

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| PR-3 편집 페이지 회귀 | 중간 | E2E 스모크 테스트. DocentSection 분리 전후 수동 비교 |
| i18n CI 오탐 (의도적 locale 차이) | 낮음 | allowlist 주석 메커니즘 추가. 초기 실행 결과 검토 후 확정 |
| alt sweep 범위 과대 (의도적 decorative img) | 낮음 | decorative img는 `alt=""` 명시 (WCAG 기준 준수) |
| rate limit Redis 미구성 환경 | 낮음 | Redis 미연결 시 rate limit skip 처리 (기존 패턴 따름) |

---

## Version History

| 버전 | 날짜 | 변경사항 |
|------|------|---------|
| 0.1 | 2026-05-05 | CO-1 design 초안. 11항목 → 6 PR 매핑. 각 PR 변경 파일/검증 명령/예상 시간 명시. alembic 신규 없음. | itpe-ince (Claude Sonnet 4.6) |
