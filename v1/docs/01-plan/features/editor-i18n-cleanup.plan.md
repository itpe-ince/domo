---
template: plan
version: 1.0
feature: editor-i18n-cleanup
date: 2026-05-01
author: itpe-ince (Claude Opus 4.7)
project: domo
project_version: v1
parent_pdca: editor-responsive-redesign (#3, archived 2026-05-01)
---

# editor-i18n-cleanup Planning Document

> **Summary**: editor-responsive-redesign(#3) Match Rate 96%로 archive되었으나, 비-wizard 영역(EditorWorkspace / ProductFields / PostPreviewCard / EditorStepContent prompt)에 한국어 hardcode가 잔존. 이미 정의된 `post.*` i18n 키와 일부 신규 키를 사용해 ko 외 4개 locale에서 부분 한국어 노출 문제를 해소한다. 백엔드 변경 0, 신규 컴포넌트 0.
>
> **Status**: Draft (carry-over from #3 minor m-2)
> **Sub-PDCA**: Carry-over feature (not in original 11-feature roadmap)

---

## 1. Overview

### 1.1 Purpose

editor-responsive-redesign(#3) 분석 보고서의 minor gap **m-2**: 비-wizard 영역에 한국어 hardcode 잔존 — `EditorWorkspace.tsx`, `ProductFields.tsx`, `PostPreviewCard.tsx`, 그리고 `EditorStepContent.tsx`의 `prompt(...)` 호출. ProductFields의 `verbatim 보존` 정책(회귀 0 우선)으로 인한 의식적 결과이며, 회귀 위험 없이 후속 PDCA에서 정리 가능.

영향 범위: 한국어가 아닌 locale(en/ja/zh/es) 사용자에게 편집 폼·미리보기 카드 일부에서 한국어 텍스트 노출.

### 1.2 Background

- 부모 PDCA #3 분석 결론: AC-7(5 locale 레이아웃 깨짐 0)은 wizard/preview 영역 한정 검증 — 통과했으나 비-wizard 영역은 검증 범위 외
- 다수 텍스트가 이미 [v1/frontend/src/i18n/ko.json](../../../frontend/src/i18n/ko.json) `post.*` 블록에 키로 정의되어 있음에도 컴포넌트가 사용하지 않음
- ProductFields는 PDCA #3에서 `verbatim` 보존 명시 (헤더 docstring `L7-9`) — 안전한 점진 정리 차원에서 본 PDCA로 분리

### 1.3 Related Documents

- 부모 PDCA #3: [v1/docs/archive/2026-05/editor-responsive-redesign/](../../archive/2026-05/editor-responsive-redesign/)
- 분석 보고서 m-2: 위 archive 폴더의 `editor-responsive-redesign.analysis.md` §4 m-2
- 자매 carry-over: `i18n-time-formatting`(#2 PDCA carry-over, `formatRelativeTime` 한국어 hardcode + `lastSavedAgo` 키)

---

## 2. Scope

### 2.1 In Scope

#### A. 기존 i18n 키 활용 (신규 키 추가 없음)

대상 컴포넌트와 hardcode → 기존 키 매핑:

| 파일·라인 | 현재 hardcode | 활용 가능한 기존 키 |
|-----------|---------------|---------------------|
| `EditorWorkspace.tsx:222` | `placeholder="제목"` | `post.title` |
| `EditorWorkspace.tsx:267` | `" 예약"` (날짜 뒤 라벨, 예: "2026-05-01 ... 예약") | (신규 `post.scheduledBadge` 또는 ICU `{date} 예약`) |
| `EditorWorkspace.tsx:302` | `"다음 업로드를 메이킹/타임랩스 영상으로 표시"` | `post.makingVideoLabel` |
| `EditorWorkspace.tsx:331` | `"태그"` | `post.tags` |
| `EditorWorkspace.tsx:356-357` | `"※ 이미지/영상 포함 시 디지털 아트 판독 큐에 진입합니다 (관리자 승인 필요)."` | `post.artCheckNote` |
| `ProductFields.tsx:64` | `"상품 정보"` | `post.productInfo` |
| `ProductFields.tsx:67` | `"장르"` | `post.genre` |
| `ProductFields.tsx:83` | `"크기"` | `post.dimensions` |
| `ProductFields.tsx:93` | `"매체"` | `post.medium` |
| `ProductFields.tsx:103` | `"제작 연도"` | `post.year` |
| `ProductFields.tsx:121` | `"경매로 판매"` | `post.auctionSell` |
| `ProductFields.tsx:130` | `"즉시구매 가능"` | `post.buyNow` |
| `ProductFields.tsx:134` | `"즉시구매가 (USD)"` | `post.buyNowPrice` |

#### B. 신규 키 추가 (소규모, 기존 키 없음)

| 위치 | 한국어 | 신규 키 후보 |
|------|--------|-------------|
| `EditorWorkspace.tsx:258`, `EditorStepContent.tsx:110` | `"업로드 중..."` | `post.editor.uploading` |
| `EditorWorkspace.tsx:267` | `"{date} 예약"` (badge) | `post.editor.scheduledBadge` (ICU `{{time}} 예약`) |
| `EditorWorkspace.tsx:313`, `EditorStepContent.tsx:130` | `prompt("장소명을 입력하세요 (예: 서울시립미술관)")` | `post.editor.locationPrompt` |
| `EditorStepPublish.tsx:57` | `aria-label="예약 해제"` | `post.editor.scheduledBadgeRemove` |
| `EditorStepPublish.tsx:74` | `aria-label="위치 해제"` | `post.editor.locationBadgeRemove` |
| `PostPreviewCard.tsx:168` | `"장르: {genre}"` | `post.editor.preview.genrePrefix` (ICU `장르: {{genre}}`) |
| `PostPreviewCard.tsx:170` | `"경매"` (badge) | `post.editor.preview.auctionBadge` |
| `PostPreviewCard.tsx:172` | `"즉시구매가: ${buyNowPrice}"` | `post.editor.preview.buyNowPricePrefix` (ICU `즉시구매가: {{price}}`) |

= 약 9개 신규 키 × 5 locale = 45 entries

### 2.2 Out of Scope

- `formatRelativeTime` 한국어 hardcode + `lastSavedAgo` 키 → 별도 carry-over PDCA `i18n-time-formatting`로 분리 (이미 #2 PDCA 분석에서 식별)
- Wizard/Preview 영역 신규 텍스트 추가 (이미 #3에서 완료)
- 백엔드/DB 변경
- 컴포넌트 구조 변경 (#7 `editor-product-meta`에서 처리)
- a11y 외 UX 개선

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | EditorWorkspace의 7개 hardcode 텍스트가 기존 `post.*` 키 또는 신규 `post.editor.*` 키 사용으로 외재화 | High | Pending |
| FR-02 | ProductFields의 8개 hardcode 텍스트가 기존 `post.{productInfo,genre,dimensions,medium,year,auctionSell,buyNow,buyNowPrice}` 키 사용 | High | Pending |
| FR-03 | PostPreviewCard의 3개 hardcode 텍스트(`장르:`, `경매`, `즉시구매가: $`)가 신규 키로 외재화 | High | Pending |
| FR-04 | EditorStepContent/EditorStepPublish의 prompt + aria-label 외재화 | Medium | Pending |
| FR-05 | 신규 키 5 locale 모두 정의 (ko/en/ja/zh/es) — 누락 0 | High | Pending |
| FR-06 | 회귀 0 — #3에서 검증된 8 AC + 5 통합 지점 모두 동작 동일 | High | Pending |
| FR-07 | TypeScript 0 에러 + JSON 5 locale valid | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement |
|----------|----------|-------------|
| Coverage | 비-wizard 영역 한국어 hardcode 0 (`grep -rn "[가-힣]"`로 자동 검증) | grep 결과 0 (단, 주석/docstring 제외) |
| Locale parity | 5 locale 모두 신규 키 100% 정의 | JSON 비교 |
| 회귀 | TypeScript 0 에러, 데스크탑/모바일 5 통합 지점 동작 동일 | tsc + 수동 회귀 5개 시나리오 |

---

## 4. Acceptance Criteria

| ID | 기준 | 검증 |
|----|------|------|
| AC-1 | EditorWorkspace에서 한국어 hardcode 0 (주석 제외) | `grep "[가-힣]" EditorWorkspace.tsx \| grep -v "^ *\*\| //"` |
| AC-2 | ProductFields에서 한국어 hardcode 0 (주석 제외) | grep |
| AC-3 | PostPreviewCard에서 한국어 hardcode 0 (주석 제외) | grep |
| AC-4 | en locale에서 `/posts/new` 진입 → 모든 폼 라벨/placeholder/badge가 영어로 표시 | 수동 |
| AC-5 | ja/zh/es 동일 확인 | 수동 |
| AC-6 | 한국어 locale 진입 시 표시 텍스트가 #3 archive 시점과 동일 (회귀 0) | 수동 비교 |
| AC-7 | TypeScript `npx tsc --noEmit` 0 에러 | CI |
| AC-8 | 5 locale JSON 모두 valid | `node -e "JSON.parse(...)"` |

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|:---------:|------------|
| ICU 보간 구문 오류 (`{{time}}`, `{{genre}}`) | Medium | Low | 기존 `post.draft.lastSavedAgo: "{{time}} 전"` 패턴 따름 (이미 사용 중) |
| 5 locale 중 1개 누락 | High (FR-05 위반) | Low | 신규 키 추가 시 5 locale 동시 작성 + JSON valid 검증 |
| ProductFields 변경이 #7 `editor-product-meta`와 충돌 | Medium | Low | 본 PDCA는 prop surface 미변경, 내부 JSX 라벨만 t() 적용 — #7은 ProductFields 내부 재작성이므로 자연 흡수 |
| 한국어 텍스트 retro-fit 시 일부 길이 변화로 layout 미세 변화 | Low | Medium | 텍스트 길이 큰 변화 없음 (한자/영문은 한국어보다 짧거나 비슷). truncate 적용된 곳은 영향 없음 |

---

## 6. Architecture Considerations

### 6.1 Project Level

기존 Dynamic 유지. 변경 없음.

### 6.2 Key Decisions

| Decision | Selected | Rationale |
|----------|---------|-----------|
| 신규 키 네임스페이스 | `post.editor.*` 확장 | #3에서 만든 블록 구조 그대로 활용 |
| ICU 보간 구문 | `{{varName}}` (Mustache 스타일) | 기존 `post.draft.lastSavedAgo` 동일 패턴 |
| 적용 순서 | 기존 키 활용(13개 위치) → 신규 키 9개 추가 → 5 locale 갱신 → 컴포넌트 t() 호출 | 회귀 위험 최소화 (기존 키만 활용하는 위치는 신규 키 추가 없이 즉시 적용 가능) |

---

## 7. Convention Prerequisites

기존 i18n 컨벤션 그대로 유지:
- `post.*`는 포스트 도메인 텍스트
- `post.editor.*`는 에디터 페이지 전용 텍스트 (PDCA #3에서 도입)
- ICU 보간 구문 `{{varName}}`

---

## 8. Phased Delivery

### Phase 1 (XS, ~1 hour): 기존 키 활용 위치 정리
- [ ] EditorWorkspace.tsx 5개 위치 (`title`, `tags`, `makingVideoLabel`, `artCheckNote`, `productInfo` 활용 안 함이지만 ProductFields에서)
- [ ] ProductFields.tsx 8개 위치 (`productInfo`, `genre`, `dimensions`, `medium`, `year`, `auctionSell`, `buyNow`, `buyNowPrice`)
- [ ] tsc 검증

### Phase 2 (XS, ~30 min): 신규 키 추가
- [ ] `post.editor.uploading`, `scheduledBadge`, `locationPrompt`, `scheduledBadgeRemove`, `locationBadgeRemove`, `preview.genrePrefix`, `preview.auctionBadge`, `preview.buyNowPricePrefix` = 9 키 × 5 locale = 45 entries
- [ ] JSON valid 검증

### Phase 3 (XS, ~30 min): 신규 키 적용 + 회귀 검증
- [ ] EditorWorkspace.tsx 잔여 3개 (`uploading`, `scheduledBadge`, `locationPrompt`)
- [ ] EditorStepContent.tsx 2개 (`uploading`, `locationPrompt`)
- [ ] EditorStepPublish.tsx 2개 (`scheduledBadgeRemove`, `locationBadgeRemove`)
- [ ] PostPreviewCard.tsx 3개
- [ ] tsc 검증
- [ ] 사용자 5 locale × 데스크탑/모바일 수동 회귀

총 예상: **~2 hours, XS** 규모

---

## 9. Next Steps

1. [ ] 본 plan 사용자 승인
2. [ ] `/pdca design editor-i18n-cleanup` 또는 plan만으로 충분하므로 design 생략 → `/pdca do`로 직접 진입 (XS 규모 + 패턴 명확)
3. [ ] Phase 1-3 순차 진행
4. [ ] `/pdca analyze` → ≥ 90% 시 `/pdca report` → `/pdca archive --summary`

---

## 10. Open Questions

| ID | 질문 | 옵션 | 권장 default |
|----|------|------|:------------:|
| OQ-1 | design 단계 생략 가능 여부 (XS 규모, 패턴 명확) | A 생략(plan만으로 do) / B 생략 안 함 | **A** — i18n 외재화 패턴이 #3에서 이미 확립됨 |
| OQ-2 | `prompt()` 호출은 i18n 적용 가능하지만 `prompt()` 자체가 native 다이얼로그 — 별도 모달로 교체 여부 | A 그대로(t() 적용만) / B 모달로 교체 | **A** — 모달 교체는 별도 UX PDCA로 분리 (`location-input-modal`) |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-01 | Initial draft from #3 m-2 carry-over. 13개 기존 키 활용 + 9개 신규 키 추가 = 22 위치 정리 계획 | itpe-ince (Claude Opus 4.7) |
| 0.2 | 2026-05-03 | **#4 (editor-media-ux) 분석 결과 통합**: (a) m-2 `post.editor.media.uploading` dead key 제거 또는 retry-UI에서 활용 검토, (b) m-3 `EditorStepContent.tsx:120-122` 인라인 `"업로드 중..."` 한국어 잔존 1줄 제거, (c) m-4 #3 carry-over 잔존(EditorWorkspace 한국어 5건 + EditorStepContent prompt 1건) 통합 처리. 본 PDCA의 작업 항목이 +3 추가됨 — 위치 약 25곳으로 확장 | itpe-ince (Claude Opus 4.7) |
