# PDCA Completion Report — Domo Artist Onboarding Phase 1

**Feature**: domo-artist-onboarding (Phase 1: 프로필 필드 확장)
**Period**: 2026-04-14
**Final Match Rate**: 🟢 **97%**
**Status**: ✅ Completed

---

## 1. Executive Summary

Domo Lounge 플랫폼의 **작가 가입/심사 체계**를 고객 요구사항에 맞게 확장한 작업.
기존 텍스트 기반 단순 신청서를 **4단계 위저드 형태**의 구조화된 심사 신청 폼으로
전면 리팩터하고, 작가 프로필에 학과/졸업연도/장르태그/대표작품/전시·수상 이력 등
13개 필드를 추가했다.

### 핵심 지표

| 지표 | 값 |
|---|---|
| 신규 파일 | 8개 (컴포넌트 7 + 마이그레이션 1) |
| 수정 파일 | 6개 (모델, 스키마, API 3, 타입) |
| Match Rate | 93% → **97%** (1회 iterate) |
| 등급 체계 변경 | 4개 명칭 변경 (student/emerging/recommended/popular) |
| 프로필 필드 | 기존 5개 → **18개** |

---

## 2. Scope Delivered

### 2.1 Backend

| 파일 | 변경 |
|---|---|
| `alembic/versions/0014_artist_onboarding.py` | 신규 — artist_applications 8컬럼 + artist_profiles 7컬럼 + badge 명칭 마이그레이션 |
| `models/user.py` | ArtistApplication: department, graduation_year, is_enrolled, genre_tags, enrollment_proof_url, representative_works, exhibitions, awards 추가. ArtistProfile: 동일 7컬럼 + badge_level 기본값 `student` |
| `schemas/artist.py` | 전면 재작성: RepresentativeWork, HistoryEntry Pydantic 모델, statement 200자 제한, representative_works 3~6개 검증, genre_tags 1~5개 검증, BADGE_LABELS 매핑 |
| `api/artists.py` | POST /artists/apply 핸들러에 신규 필드 저장 (JSONB 변환 포함) |
| `api/admin.py` | 승인 시 ArtistProfile에 신규 필드 복사 + badge 자동 결정 (is_enrolled → student/emerging) |
| `api/users.py` | GET /users/{id} 프로필 응답에 13개 신규 필드 + badge_label 포함 |

### 2.2 Frontend

| 파일 | 변경 |
|---|---|
| `components/artist-apply/types.ts` | 신규 — ApplicationFormData, StepProps, GENRES 공유 타입 |
| `components/artist-apply/StepBasicInfo.tsx` | 신규 — Step 1: 학교/학과/졸업연도/재학/장르태그 |
| `components/artist-apply/WorkCard.tsx` | 신규 — 개별 작품 입력 카드 (이미지 업로드 내장) |
| `components/artist-apply/StepWorks.tsx` | 신규 — Step 2: WorkCard 3~6개 관리 |
| `components/artist-apply/StepPortfolio.tsx` | 신규 — Step 3: 자기소개(200자) + 증빙 업로드 + URL |
| `components/artist-apply/HistoryEntryRow.tsx` | 신규 — 전시/수상 개별 입력 행 |
| `components/artist-apply/StepHistory.tsx` | 신규 — Step 4: 전시/수상 동적 추가/삭제 |
| `app/artists/apply/page.tsx` | 전면 리팩터: 4단계 위저드 + 프로그레스 바 + canNext 검증 |
| `lib/api.ts` | RepresentativeWork, HistoryEntry 타입 + ApplyArtistInput 확장 + ArtistApplication 타입 확장 |

---

## 3. Design Decisions

### D1. 4단계 위저드 (vs 단일 폼)

**선택**: Step 1(기본정보) → Step 2(대표작품) → Step 3(포트폴리오) → Step 4(이력)
**이유**: 13개 필수/선택 필드를 한 화면에 배치하면 압도적. 단계별로 분리하면 사용자가 집중 가능. 각 단계 `canNext` 검증으로 불완전 제출 방지.

### D2. 등급 체계 명칭 변경

**선택**: emerging→student, featured→emerging, popular→recommended, master→popular
**이유**: 고객 확정 — "학생/신진작가/추천작가/인기작가"가 플랫폼 정체성에 부합. 학교 인증 기반 등급이 핵심 차별점.

### D3. representative_works를 JSONB로 저장

**선택**: ARRAY 대신 JSONB
**이유**: 작품명+설명+사이즈+매체+연도를 포함하는 구조화된 데이터. 별도 테이블 대신 JSONB로 저장하면 조인 없이 한 번에 조회 가능. 프로토타입 단계에서 적합.

### D4. 컴포넌트 6개 분리 (iterate에서 수행)

**선택**: types.ts + StepBasicInfo + WorkCard + StepWorks + StepPortfolio + HistoryEntryRow + StepHistory
**이유**: 단일 파일 통합 시 250줄 이상 → 가독성/유지보수 문제. 각 Step이 독립적으로 `data` + `onChange` props 패턴을 사용해 테스트/수정 용이.

---

## 4. Match Rate 추이

```
v1 (초기 분석)     ██████████████████░░ 93%
v2 (iterate)       ███████████████████░ 97%  ← 현재
                   └────────────────────┘
                    0%                 100%
```

### Iterate에서 해결한 Gap

| Gap | 수정 |
|---|---|
| G2 컴포넌트 미분리 | 7개 파일로 분리 (types + 4 Steps + WorkCard + HistoryEntryRow) |
| G3 ArtistApplication 타입 미확장 | 8개 신규 필드 추가 |

### 잔여 Gap (1개)

| Gap | 영향 | 비고 |
|---|---|---|
| G1 관리자 심사 화면 확장 | 중 | admin 앱 분리로 별도 작업. admin/src/app/applications/ 에서 확장 필드 표시 필요 |

---

## 5. 후속 Phase 로드맵

| Phase | 내용 | 의존성 | 상태 |
|---|---|---|---|
| **Phase 1** | 프로필 필드 확장 + 4단계 위저드 | 없음 | ✅ 완료 |
| Phase 2 | 학교 이메일 인증 (.edu) | 이메일 인프라 (존재) | 대기 |
| Phase 3 | 본인인증 KYC | 외부 서비스 계약 | 대기 |
| Phase 4 | 자동 전환 + 배지 산정 크론잡 | Phase 1 완료 | 즉시 가능 |

---

## 6. Artifacts

| 문서 | 경로 |
|---|---|
| Plan | `docs/01-plan/features/domo-artist-onboarding.plan.md` |
| Design | `docs/02-design/features/domo-artist-onboarding.design.md` |
| Analysis | `docs/03-analysis/domo-artist-onboarding.analysis.md` |
| Report | `docs/04-report/domo-artist-onboarding.report.md` |

---

## 7. Sign-off

- [x] Match Rate ≥ 90% (97%)
- [x] P0/P1 Gap 모두 해결
- [x] 마이그레이션 실행 확인
- [x] 프론트 `/artists/apply` 200 OK
- [x] 백엔드 health OK
