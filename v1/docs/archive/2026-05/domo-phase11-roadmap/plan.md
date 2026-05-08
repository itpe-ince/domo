---
template: plan
version: 1.0
feature: domo-phase11-roadmap
date: 2026-05-08
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 11 (Admin 콘솔 완성 + Carry-over 청산 + K-6 조건부 진입)
status: Draft (Roadmap)
---

# Domo Phase 11 — 로드맵 (Master Plan)

> **Summary**: Phase 10 종결(K-8/K-2/K-4/K-7/CO-1 5 sub-PDCA, 96.4% 가중 Match Rate, K-6 정당 이월, 2026-05-06) 후 네 가지 방향을 병행한다. Wave A: 백엔드 API가 이미 존재하는 Admin 콘솔 누락 메뉴 2개(K-4/K-7 검수 큐 프론트엔드) 즉시 구현. Wave B: A/B 결과 분석 페이지 + Diversity 튜닝 페이지 프론트엔드 완성. Wave C: K-6 AI 가격 추천(거래 ≥ 100건 조건부). Wave D: carry-over 청산 3개(키보드 단축키, audit_logs DB, 가입 다양화). 총 8 sub-PDCAs, 6~8주 예상.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-08
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 11 배경 & 전략적 의미

### Phase 10 종결 성과 요약

Phase 10은 K Wave 2(K-8/K-2/K-4/K-7 4개) + CO-1(Phase 9 carry-over 11항목 청산) = 5 sub-PDCA 100% 종결(K-6 정당 이월). 주요 성과:

- **ML 운영 측정 인프라 완성**: K-8 PostHog Feature Flag A/B 테스트(alembic 0080) + K-2 Diversity Reranking(alembic 0081)
- **AI 큐레이션 자동화**: K-4 Featured Artist 주간 자동 선정(alembic 0082) + K-7 AI 컬렉션 K-means 클러스터링(alembic 0083)
- **K-6 정당 이월**: auctions.status='sold' < 100건 미충족, 강제 진행 금지
- **누적 지표**: 테스트 581 → 646 (+65), alembic 0080~0083 (4 마이그레이션, single head `0083_ai_collections`), cron 21 → 23 (+2)

### Phase 11이 중요한 이유

Phase 10 가이드 v2 정본화(2026-05-08) 과정에서 두 가지 중요한 발견이 있었다:

**1. Admin 콘솔 구현 격차**: 백엔드 API는 완성됐으나 프론트엔드 UI가 미구현된 admin 메뉴가 7개 존재한다. 이 중 운영에 직결되는 4개(K-4 검수 큐, K-7 검수 큐, A/B 결과, Diversity 튜닝)는 Phase 11에서 즉시 구현이 필요하다. API가 준비된 상태에서 UI가 없으면 운영자가 admin Python REPL이나 직접 DB 조작에 의존해야 한다는 뜻이다.

**2. 사용자 경험 격차**: 가입/로그인 방식이 Google OAuth 1종뿐이다. README 비전("동유럽이든 남미든 동아시아든")의 글로벌 접근성과 상충한다. 이메일+비밀번호 가입은 가장 보편적인 방법으로 D-3에서 우선 구현한다.

```
[Phase 10 결과]
  K-8/K-2/K-4/K-7 ML 백엔드 완성 → Admin 콘솔 UI 격차 발생
  CO-1 carry-over 청산 → 추가 carry-over 식별 (키보드 단축키, audit_logs, 가입 다양화)
  K-6 거래 100건 미달 → Phase 11 조건 재확인
      ↓
[Phase 11 Wave A] Admin 큐 UI 즉시 구현 (K-4 검수 + K-7 검수)
      ↓ (병행)
[Phase 11 Wave D] Carry-over 청산 (D-1 단축키 + D-2 audit_logs + D-3 가입 다양화)
      ↓ (Wave A 완료 후)
[Phase 11 Wave B] Admin 분석/튜닝 UI (K-8 실험 결과 + K-2 diversity 튜닝)
      ↓ (조건부)
[Phase 11 Wave C] K-6 AI 가격 추천 (거래 ≥ 100건 시)
```

---

## 1. 비즈니스 컨텍스트

### Phase 10 → Phase 11 전환

Phase 10에서 "ML이 작품을 올바른 사람에게 추천하고, 그 효과를 측정한다"는 단계가 완성됐다. Phase 11은 **운영자가 ML 결과를 직접 보고 조율할 수 있는 Admin 제어판** 구현과 **플랫폼 접근성 기반 확대**가 목표다.

```
Phase 10까지의 Domo: ML이 자동 추천 → 백엔드에서 결과 생성, 운영자는 직접 확인 불가
Phase 11의 Domo: Admin 콘솔에서 ML 결과 확인 + 파라미터 튜닝 + 검수 큐 운영
```

### Phase 11이 README 비전을 완성하는 이유

| README 비전 | Phase 10 달성 | Phase 11 달성 |
|-------------|:----------:|:----------:|
| **"유저들이 늘어나야 소비자들도 늘어남"** | K-8 A/B 인프라로 ML 피드 효과 측정 ✅ | B-1 A/B 결과 Admin 대시보드 → ML 피드 v2 전체 rollout 결정 가속 |
| **"전 세계 아티스트들의 인덱스"** | K-4 신진작가 자동 선정 ✅ | A-1 Admin 큐 UI → 운영자가 주간 Featured Artist 직접 검수·결정 |
| **"동유럽이든 남미든 동아시아든 — 꿈과 희망"** | K-2 지역 다양성 제약 ✅ | D-3 이메일+비밀번호 가입 → 구글 계정 없는 지역 접근 가능 |
| **"컬렉터들한테는 회비"** | K-7 AI 컬렉션 자동 생성 ✅ | A-2 Admin 큐 UI → 운영자가 Editor's Pick 컬렉션 직접 검수·편집 |
| **"신진 작가들의 거래 이루어지면 인덱스"** | K-4 ML 스코어 선정 ✅ | C-1 AI 가격 추천(거래 100건+ 시) → reserve_price 진입 장벽 ↓ |
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | K-6 이월 → 준비 중 | C-1 진입 → AI 가격 추천으로 적정가 책정 → 낙찰률 ↑ → 생존 가능성 ↑ |

---

## 2. Phase 10 결과 → Phase 11 매핑

| Phase 10 산출물 | Phase 11 활용 | sub-PDCA |
|--------------|:------------|:--------:|
| K-4 `featured_artist_candidates` 테이블 + API 4개 | A-1 Admin 큐 UI 구현 (백엔드 완성, 프론트 미구현) | A-1 |
| K-7 `ai_collections` 테이블 + API 5개 | A-2 Admin 큐 UI 구현 (백엔드 완성, 프론트 미구현) | A-2 |
| K-8 `ml_experiments` + PostHog Experiment API | B-1 Admin 실험 결과 분석 페이지 | B-1 |
| K-2 `diversity_configs` + PATCH API | B-2 Admin Diversity 튜닝 페이지 | B-2 |
| alembic 0083 head → 0084 예약 | C-1 K-6 (거래 ≥ 100건 시 진입) | C-1 |
| user-system-guide gap: 키보드 단축키 12개 미구현 | D-1 전역 hotkey 구현 (8~12개) | D-1 |
| admin-system-guide gap: audit_logs 테이블 미존재 | D-2 alembic 0084 audit_logs 테이블 | D-2 |
| user-system-guide gap: 가입 방법 Google 1종뿐 | D-3 이메일+비밀번호 가입 (1순위) | D-3 |
| K-1 ML 피드 v2 14일 운영 → 결과 분석 | B-1 PostHog 임베드 결과 → ML_FEED_DEFAULT_ALGO 전체 rollout 결정 | B-1 |

### Admin 콘솔 누락 메뉴 현황

Phase 10 가이드 v2 분석(admin-system-guide.gap-analysis.md §2)에서 식별된 누락 메뉴 7개:

| 우선도 | 메뉴 경로 | 백엔드 API | Phase 11 Wave |
|:-----:|----------|:----------:|:------------:|
| 🔥 High | `/admin/featured-artist/queue` (K-4 검수 큐) | ✅ 4개 endpoint | Wave A |
| 🔥 High | `/admin/ai-collections/queue` (K-7 검수 큐) | ✅ 5개 endpoint | Wave A |
| ⚡ Medium | `/admin/experiments` (K-8 A/B 결과) | ✅ 3개 endpoint | Wave B |
| ⚡ Medium | `/admin/diversity-config` (K-2 튜닝) | ✅ 2개 endpoint | Wave B |
| ⏳ Low | `/admin/analytics` 통합 | ⚠️ 일부 | Wave C 또는 Phase 12 |
| ⏳ Low | `/admin/payouts` (정산 관리) | ⚠️ 일부 | Wave C 또는 Phase 12 |
| ⏳ Low | `/admin/system` (cron 모니터) | ❌ 백엔드 미구현 | Phase 12 이월 |

---

## 3. README 비전 직접 매핑

> README 원문 직접 인용 → Phase 11 구현 매핑

| README 원문 | Phase 11 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| **"유저들이 늘어나야 소비자들도 늘어남 — 그로스해킹"** | **B-1** | Admin K-8 결과 분석 페이지로 ML 피드 v2 효과(CTR ↑) 직접 확인 → ML_FEED_DEFAULT_ALGO=v2 rollout 결정 → 신규 사용자 유입 가속 |
| **"전 세계 아티스트들의 인덱스를 만들고 싶음"** | **A-1** | Admin Featured Artist 큐 UI → 운영자가 주간 신진작가 검수/승인. 실시간 글로벌 신진작가 인덱스 발행 |
| **"동유럽이든 남미든 동아시아든 — 꿈과 희망"** | **D-3** | 이메일+비밀번호 가입 추가 → 구글 계정 없는 신흥 시장 사용자 진입 장벽 제거 |
| **"컬렉터들한테는 회비 1년에 10분씩"** | **A-2** | Admin AI 컬렉션 검수 큐 UI → Editor's Pick 컬렉션 검수·편집·발행. 컬렉터 탐색 경험 주간 업데이트 |
| **"신진 작가들의 거래 이루어지면 인덱스 만들고"** | **C-1** | AI 가격 추천으로 reserve_price 진입 불안 해소 → 경매 등록률 ↑ → 낙찰 건수 ↑ → 인덱스 정교화 |
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | **C-1, D-3** | C-1 AI 가격 추천으로 적정 낙찰가 안내 + D-3 이메일 가입으로 더 많은 신진작가 진입 가능 |
| **"히스토리를 두세 개 만든다"** | **A-2** | AI 컬렉션 운영자 편집 → 스토리가 있는 큐레이션 발행 → 언론/SNS 확산 가능한 발견 스토리 주간 생성 |

---

## 4. Sub-PDCA 상세 (8개)

### Wave A — 운영 차단 요소 해제 (즉시 진입, ~3주, 2 agents 병렬)

백엔드 API는 완성됐으나 Admin 콘솔 프론트엔드가 없어 운영자가 수동으로 DB를 조작해야 하는 상황을 해제한다.

---

#### A-1: `/admin/featured-artist/queue` UI (K-4 검수 큐 프론트엔드)

**Feature ID**: `admin-featured-artist-queue-ui`
**우선순위**: Must (운영 차단 — K-4 백엔드 완성, 프론트 미구현)
**Wave**: Wave A (즉시 진입)
**예상 기간**: ~10일
**의존성**: K-4 백엔드 API (Phase 10, ✅ 완성): `GET /admin/featured-artist/candidates`, approve/publish/reject 4개 endpoint
**담당 agent**: frontend-architect

**Goal**

K-4에서 구축한 주간 Featured Artist 자동 추천 시스템의 Admin 검수 큐 UI를 구현한다. 운영자가 Admin 콘솔에서 ML 추천 후보 목록을 검토하고, 승인/거부를 할 수 있게 한다. 현재는 API만 있고 UI가 없어 DB 직접 조작이 필요한 상태다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/featured-artist/queue`
  - `GET /admin/featured-artist/candidates` → 이번 주 ML 추천 후보 목록 (최대 5명)
  - 후보 카드: 작가명, 아바타, 스코어 breakdown JSONB 시각화 (engagement 30%, rank 30%, diversity 20%, 신진 20%), 최근 작품 썸네일 3개
  - status별 탭: `pending` / `approved` / `rejected`
- **승인/거부 인터랙션**:
  - `POST /admin/featured-artist/{id}/approve` → 승인 (publish 대기)
  - `POST /admin/featured-artist/{id}/publish` → 즉시 홈 노출
  - `POST /admin/featured-artist/{id}/reject` + 사유 입력 textarea
  - OQ-6 권장: autopublish OFF 정책 유지 (approve ≠ 자동 publish)
- **배지 + 상태 표시**:
  - 신진작가(팔로워 < 1000) 배지 강조
  - "최근 4주 내 선정 이력" 경고 표시
  - 미검수 48h 초과 시 UI 하이라이트 (Slack 알림과 연동)
- **스코어 설명 툴팁**: breakdown 4개 가중치 의미 한국어 설명
- **Admin 콘솔 사이드바 메뉴 추가**: `AdminShell.tsx`에 `/admin/featured-artist` 메뉴 항목 추가
- **i18n**: 5 locale 키 `admin.featured_artist.*` (10~15개)

**Acceptance Criteria**

- [ ] `/admin/featured-artist/queue` 페이지 로드 → ML 후보 목록 표시 확인
- [ ] 스코어 breakdown (4개 가중치) 시각화 표시 확인
- [ ] 승인 → approve API 호출 → status `approved` 변경 확인
- [ ] 거부 → reject API + 사유 입력 → status `rejected` 변경 확인
- [ ] publish → 홈 화면 Featured Artist 섹션 즉시 반영 확인
- [ ] Admin 콘솔 사이드바 메뉴 동작 확인 (2FA 검증 통과)
- [ ] 5 locale i18n 키 표시 확인
- [ ] tsc 0 errors, lint 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 스코어 breakdown JSONB 구조 변경 가능성 | 낮음 | K-4 alembic 0082 스키마 확인 후 UI 구현 |
| Admin 콘솔 라우팅 패턴 불일치 | 중간 | `AdminShell.tsx` 기존 페이지 패턴 우선 준수 |
| approve 후 publish 혼동 (2단계) | 중간 | UI에 approve/publish 2단계 워크플로 명확히 표시 |

**KPIs**

- K-4 Admin 검수 큐 운영 시작 (weekly cron 후 수동 DB 조작 0건)
- 주간 Featured Artist 검수 리드타임: 48h 이내

---

#### A-2: `/admin/ai-collections/queue` UI (K-7 검수 큐 프론트엔드)

**Feature ID**: `admin-ai-collections-queue-ui`
**우선순위**: Must (운영 차단 — K-7 백엔드 완성, 프론트 미구현)
**Wave**: Wave A (A-1과 병렬)
**예상 기간**: ~10일
**의존성**: K-7 백엔드 API (Phase 10, ✅ 완성): `GET /admin/collections/pending`, approve/edit/reject 5개 endpoint
**담당 agent**: frontend-architect

**Goal**

K-7에서 구축한 AI 큐레이션 컬렉션("Editor's Pick") 자동 생성 시스템의 Admin 검수 큐 UI를 구현한다. 운영자가 LLM 생성 컬렉션 제목/설명을 검토·편집하고 발행할 수 있게 한다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/ai-collections/queue`
  - `GET /admin/collections/pending` → 검수 대기 컬렉션 목록
  - 컬렉션 카드: 제목(한국어), 테마 태그, 클러스터 k값, 포함 작품 10개 그리드 썸네일, 생성 시각
  - 5 locale 제목/설명 탭 전환 (ko/en/ja/zh/es)
- **편집 + 발행 인터랙션**:
  - `PATCH /admin/collections/{id}` → 제목/설명 수동 편집 (5 locale 각각 편집 가능)
  - `POST /admin/collections/{id}/approve` (publish = 발행) → `/explore/collections` 노출
  - `POST /admin/collections/{id}/archive` → 미발행 보관
  - OQ-6 권장: autopublish OFF 정책 유지
- **컬렉션 상세 미리보기**: 발행 전 `/explore/collections/{id}` 렌더링 미리보기 (iframe 또는 별도 탭)
- **LLM 비용 표시**: 이번 주 LLM 사용 비용 + 일 $5 한도 대비 현황 표시
- **Admin 콘솔 사이드바 메뉴 추가**: `AdminShell.tsx`에 `/admin/ai-collections` 메뉴 항목 추가
- **i18n**: 5 locale 키 `admin.collections.*` (10~15개)

**Acceptance Criteria**

- [ ] `/admin/ai-collections/queue` 페이지 로드 → 대기 컬렉션 목록 표시 확인
- [ ] 5 locale 제목/설명 탭 전환 동작 확인
- [ ] 수동 편집(PATCH API) → 저장 확인
- [ ] 발행(approve) → `/explore/collections` 페이지 반영 확인
- [ ] 아카이브 → status='archived' 변경 확인
- [ ] LLM 비용 현황 표시 확인
- [ ] Admin 콘솔 사이드바 메뉴 동작 확인
- [ ] tsc 0 errors, lint 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 5 locale 편집 폼 UX 복잡도 | 중간 | 탭 UI로 locale 전환, 한 번에 1개 locale만 편집 |
| 컬렉션 작품 그리드 이미지 로딩 성능 | 낮음 | 썸네일 lazy loading + 최대 10개 제한 |

**KPIs**

- K-7 Admin 검수 큐 운영 시작 (weekly cron 후 수동 DB 조작 0건)
- 주간 컬렉션 검수 리드타임: 48h 이내
- 컬렉션 admin 승인율: ≥ 70%

---

### Wave B — 운영 효율 (Wave A 완료 후, ~3주, 2 agents 병렬)

---

#### B-1: `/admin/experiments` UI (K-8 A/B 결과 분석 페이지)

**Feature ID**: `admin-experiments-ui`
**우선순위**: Should
**Wave**: Wave B (Wave A 완료 후)
**예상 기간**: ~10일
**의존성**: K-8 백엔드 API (Phase 10, ✅ 완성): `GET /admin/experiments`, `POST /admin/experiments`, `GET /admin/experiments/{name}/results`
**담당 agent**: frontend-architect

**Goal**

K-8 ML A/B 테스트 인프라 위에서 운영자가 실험 결과를 직접 확인하고, ML 피드 v2 전체 rollout 여부를 데이터 기반으로 결정할 수 있는 Admin 대시보드를 구현한다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/experiments`
  - `GET /admin/experiments` → 실험 목록 (running/paused/completed)
  - 실험 카드: 이름, flag_key, 시작일, 기간, 현재 상태
  - 실험별 상세 결과 페이지 `/admin/experiments/{name}`
- **결과 시각화 (OQ-2 권장: PostHog Insights 임베드)**:
  - PostHog Experiment 결과 임베드 (iframe 또는 PostHog embed URL)
  - Feed CTR v1 vs v2 비교 (control vs treatment)
  - 통계적 유의성 p-value 표시
  - Session duration delta 표시
  - 후원 전환율 baseline 표시
  - 14일 운영 결과 기준 권장 rollout 결정 박스
- **실험 제어**:
  - `POST /admin/experiments` → 신규 실험 생성 (flag_key + 설명 입력)
  - 실험 pause/resume (PostHog Feature Flag 토글 연동)
- **ML_FEED_DEFAULT_ALGO rollout 결정 UI**:
  - A/B 결과 기준 권장 결정: "v2로 전환 권장" / "v1 유지 권장" / "측정 연장 권장"
  - 결정 버튼 → `/admin/settings`의 `ML_FEED_DEFAULT_ALGO` env값 변경 (PATCH `/admin/settings/{key}`)
- **Admin 콘솔 사이드바 메뉴 추가**
- **i18n**: 5 locale 키 `admin.experiments.*`

**Acceptance Criteria**

- [ ] `/admin/experiments` 실험 목록 표시 확인
- [ ] PostHog 결과 임베드 또는 API 결과 차트 표시 확인
- [ ] p-value + CTR delta 수치 표시 확인
- [ ] rollout 권장 결정 UI 표시 확인
- [ ] ML_FEED_DEFAULT_ALGO 변경 → `PATCH /admin/settings/ML_FEED_DEFAULT_ALGO` 동작 확인
- [ ] tsc 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| PostHog 임베드 CSP 제한 | 중간 | PostHog API로 결과 직접 fetch + 자체 차트 렌더링으로 fallback |
| A/B 통계 오해 (p-value 미해석) | 낮음 | UI에 간단한 해석 가이드 툴팁 추가 |

**KPIs**

- ML 피드 v2 rollout 결정 데이터 기반 수행 (A/B 결과 화면에서 직접 결정)
- 실험 결과 확인 리드타임: Admin 콘솔에서 30초 이내

---

#### B-2: `/admin/diversity-config` UI (K-2 Diversity 튜닝 페이지)

**Feature ID**: `admin-diversity-config-ui`
**우선순위**: Should
**Wave**: Wave B (B-1과 병렬)
**예상 기간**: ~7일
**의존성**: K-2 백엔드 API (Phase 10, ✅ 완성): `GET /admin/diversity-config`, `PATCH /admin/diversity-config/{name}`
**담당 agent**: frontend-architect

**Goal**

K-2 Diversity Reranking의 파라미터(장르 최소 종류, 지역 최소 종류, 신진작가 부스팅 비율, lambda 가중치)를 Admin 콘솔에서 직접 튜닝할 수 있게 한다. 현재는 API만 있고 운영자가 curl로만 변경 가능하다.

**Scope**

- **Admin 콘솔 신규 페이지**: `/admin/diversity-config`
  - `GET /admin/diversity-config` → 현재 다양성 설정값 목록
  - 설정 폼: genre_min_count (슬라이더 1~10), region_min_count (슬라이더 1~5), newcomer_boost_pct (슬라이더 0~50%), lambda_weight (슬라이더 0.0~1.0)
  - 현재 적용값 vs 편집값 비교 표시
- **변경 적용**:
  - `PATCH /admin/diversity-config/{name}` → 저장
  - OQ-7 권장: Redis 5분 캐시 자연 만료 (변경 즉시 DB 반영, 캐시는 5분 내 갱신)
  - 변경 이력 표시 (updated_at + 이전값 기록)
- **영향도 미리보기 (선택)**:
  - 현재 설정으로 오늘 피드 top-20의 장르/지역 분포 프리뷰 (GET API 연동)
- **Admin 콘솔 사이드바 메뉴 추가**
- **i18n**: 5 locale 키 `admin.diversity.*`

**Acceptance Criteria**

- [ ] `/admin/diversity-config` 현재 설정값 표시 확인
- [ ] 폼 편집 → PATCH API 호출 → DB 값 변경 확인
- [ ] Redis 5분 캐시 만료 후 새 값 적용 확인
- [ ] 변경 이력 표시 확인
- [ ] tsc 0 errors

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| lambda_weight 과도 설정 → ML 품질 저하 | 높음 | 슬라이더 범위 제한 + 경고 문구 표시 |
| 변경 이력 DB 저장 미구현 | 낮음 | 클라이언트 세션 이력만 표시하는 것으로 MVP 수준 대응 |

**KPIs**

- Diversity 파라미터 튜닝 리드타임: curl → Admin UI 전환으로 10분 → 2분 단축
- 월 1회 튜닝 주기 준수 (OQ-7 권장)

---

### Wave C — 조건부 진입 (거래 데이터 ≥ 100건, ~2주)

---

#### C-1: K-6 AI 가격 추천 (경매 reserve_price)

**Feature ID**: `ai-price-recommendation`
**우선순위**: Should (조건부 — 거래 데이터 100건 미달 시 Phase 12 이월)
**Wave**: Wave C (거래 ≥ 100건 충족 시 진입, OQ-1 권장)
**예상 기간**: ~10일
**진입 조건**: `SELECT COUNT(*) FROM auctions WHERE status = 'sold'` ≥ 100건
**의존성**: L-A `post_embeddings` pgvector (Phase 9, ✅ 완성), Phase 5 경매 DB 구조, K-1 ML 스코어
**alembic**: **0086** (C-1 진입 시, OQ-1 권장: 진입 전 거래 카운트 즉시 확인)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작가가 경매를 등록할 때 reserve_price(최저 낙찰가)를 설정하기 어려운 문제를 해결한다. 유사 작품 임베딩(L-A pgvector) + 과거 낙찰가 중앙값 + 장르별 시장 배수를 기반으로 추천 범위(min~max)를 제공한다. Phase 10에서 거래 100건 미달로 이월된 항목이다.

**Scope**

- **진입 전 조건 확인**:
  - `SELECT COUNT(*) FROM auctions WHERE status = 'sold'` ≥ 100건 확인
  - 미달 시: Phase 11 보고서에 "거래 데이터 부족 — Phase 12 이월" 명시
- **가격 추천 알고리즘** (OQ-8 권장: 단순 비교 평균가 + 가중):
  - 유사 작품 탐색: `post_embeddings` pgvector cosine 유사도 top-5 (L-A booster)
  - 과거 낙찰가 중앙값 기반 추천가 산출
  - 작가 작품 평균가 가중 (0.4×유사작품중앙값 + 0.6×작가평균가)
  - 장르별 시장 배수: 유화 1.8×, 수채화 1.2×, 디지털 아트 0.9×, 기타 1.0×
  - 추천 범위: `[중앙값 × 0.8, 중앙값 × 1.3]` (신뢰구간 표시)
  - Fallback (거래 데이터 < 5건 장르): 장르 배수만 사용
  - ML 회귀 모델은 Phase 12 검토 (OQ-8 권장)
- **alembic 0086**: 필요 시 가격 추천 로그 테이블 (선택 — API 응답 PostHog 로깅으로 대체 가능)
- **API**:
  - `POST /auctions/price-recommend` (작품 ID + 장르 + 재료 → 추천 범위 반환, 2초 이내)
  - 응답: `{ recommended_min, recommended_max, similar_auctions_count, confidence_level }`
  - PostHog 이벤트: `auction_price_recommended`, `auction_price_applied`
- **경매 등록 UI**:
  - reserve_price 입력 필드 옆 "AI 가격 추천" 버튼
  - 추천 범위 + 근거 ("유사 작품 N개 평균 낙찰가 기준") 표시
  - "추천가 적용" 버튼으로 자동 입력
  - 면책 문구: "이 추천은 참고용이며 실제 낙찰가를 보장하지 않습니다" (5 locale i18n)

**Acceptance Criteria**

- [ ] 진입 조건(거래 ≥ 100건) 충족 확인 후 진행 (미달 시 Phase 12 이월 명시)
- [ ] `POST /auctions/price-recommend` → 추천 범위 반환 (2초 이내)
- [ ] 유사 작품 5개 이상 pgvector 유사도 기반 탐색 동작 확인
- [ ] 경매 등록 UI 추천 적용 버튼 동작 확인
- [ ] 면책 문구 5 locale 표시 확인
- [ ] PostHog `auction_price_recommended` 이벤트 로깅 확인
- [ ] 거래 데이터 < 5건 장르 → fallback 장르 배수 모드 동작 확인
- [ ] unit tests: `test_price_recommendation.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 거래 데이터 100건 미달 지속 | 높음 | OQ-1 기준: 즉시 카운트 확인 후 미달 시 Phase 12 자동 이월 |
| 낮은 추천가 → 작가 수익 저해 | 중간 | "적정 범위" 명시 + 최저가가 아님을 UI 강조 |
| 가격 앵커링 효과 | 중간 | 추천 후 자유 입력 허용 (추천 ≠ 강제) |

**KPIs** (거래 100건+ 충족 시)

- 가격 추천 사용률: 경매 등록 시 ≥ 50%
- 추천가 적용률: ≥ 30%
- 낙찰 성공률 baseline: 측정 시작

---

### Wave D — Carry-over 청산 (Wave A 완료 후 또는 Wave B와 병행, ~2주)

Phase 10 CO-1 청산 이후 가이드 v2 분석에서 새롭게 식별된 carry-over 항목 3개.

---

#### D-1: 키보드 단축키 시스템 (전역 hotkey 8~12개)

**Feature ID**: `global-hotkeys`
**우선순위**: Should
**Wave**: Wave D (Wave A 완료 후 Wave B와 병행)
**예상 기간**: ~7일
**의존성**: 없음 (독립)
**담당 agent**: frontend-architect

**Goal**

user-system-guide gap 분석에서 확인: 가이드에 12개 전역 단축키가 명시됐으나 실제 구현은 모달 Esc, 이미지 에디터 `1/2/3/4` 뿐이다. OQ-3 권장에 따라 핵심 3개 + 도움말 키 `?`를 우선 구현하고, 나머지는 점진적으로 추가한다.

**Scope**

- **`useGlobalHotkeys` hook 신규 구현** (`src/lib/hooks/useGlobalHotkeys.ts`):
  - input/textarea/contenteditable에서 단축키 비활성화
  - 모달 열림 상태에서 네비게이션 단축키 비활성화
  - cleanup 처리 (unmount 시 이벤트 리스너 제거)
- **OQ-3 권장 우선 구현 단축키 (3 + 1개)**:

  | 단축키 | 동작 | 근거 |
  |--------|------|------|
  | `j` | 피드 다음 포스트로 이동 | 가장 빈번한 피드 탐색 동작 |
  | `k` | 피드 이전 포스트로 이동 | j와 쌍, vim/GitHub 표준 |
  | `⌘S` / `Ctrl+S` | 에디터 임시저장 | 작성 중 데이터 손실 방지 |
  | `?` | 단축키 도움말 모달 토글 | OQ-9 권장: GitHub/Slack 표준 |

- **단축키 도움말 모달** (`src/components/HotkeyHelpModal.tsx`):
  - `?` 키 → 모달 열기/닫기
  - 현재 구현된 단축키 목록 표시 (확장 가능 구조)
  - Esc → 모달 닫기
  - 5 locale i18n 키: `hotkeys.*`

- **향후 확장 가능 구조**:
  - `HOTKEY_REGISTRY` 배열로 단축키 등록 → 도움말 모달 자동 반영
  - Phase 12에서 `g h`(홈 이동), `n`(새 포스트), `/`(검색) 등 추가 가능

**Acceptance Criteria**

- [ ] `useGlobalHotkeys` hook 구현 + input 내 비활성화 확인
- [ ] `j/k` → 피드 포스트 포커스 이동 확인
- [ ] `⌘S`/`Ctrl+S` → 에디터 임시저장 API 호출 확인
- [ ] `?` → 도움말 모달 토글 확인
- [ ] `Esc` → 모달 닫기 확인 (기존 FocusManager Esc와 충돌 없음)
- [ ] 5 locale i18n 키 표시 확인
- [ ] unit tests: `useGlobalHotkeys.test.ts`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 기존 Esc 핸들러(FocusManager)와 충돌 | 중간 | 이벤트 전파 순서 정의 + 모달 우선 처리 |
| `j/k` 피드 스크롤 정확도 | 낮음 | 포스트 ID 기반 ref 탐색, 뷰포트 기준 스크롤 |

**KPIs**

- user-system-guide v2 단축키 섹션 구현 일치율: 4/4 (우선 구현분)
- 키보드 네비게이션 테스트: 3개 단축키 × 5 locale × E2E green

---

#### D-2: audit_logs DB 테이블 (alembic 0084)

**Feature ID**: `audit-logs-db`
**우선순위**: Should
**Wave**: Wave D (D-1과 병렬 가능)
**예상 기간**: ~7일
**의존성**: 없음 (독립)
**alembic**: **0084** (사전 배정)
**담당 agent**: bkend-expert

**Goal**

admin-system-guide gap 분석: "모든 admin 액션은 `audit_logs` 테이블에 기록"이라고 가이드가 주장했으나 실제로는 Python 구조화 로그(`log.info("AUDIT ...")`)만 존재한다. DB 테이블을 추가해 운영 이력 추적과 규정 준수(개인정보보호법)를 실현한다.

**Scope**

- **alembic 0084: `audit_logs` 테이블 신규**:
  ```sql
  audit_logs(
    id          BIGSERIAL PRIMARY KEY,
    actor_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(100) NOT NULL,  -- 'user.suspend', 'post.delete', 'featured.approve' 등
    target_type VARCHAR(50),            -- 'user', 'post', 'auction', 'featured_artist', 'collection'
    target_id   INTEGER,
    before_data JSONB,                  -- 변경 전 상태 스냅샷
    after_data  JSONB,                  -- 변경 후 상태 스냅샷
    ip_address  INET,
    created_at  TIMESTAMPTZ DEFAULT NOW()
  )
  ```
  - 인덱스: actor_id, action, target_type + target_id, created_at DESC
  - 파티셔닝 고려 (created_at 기준, 선택 — Phase 12 검토)
- **audit middleware 구현** (`app/core/audit_middleware.py`):
  - OQ-10 권장 적용 범위: admin endpoints + sensitive user actions (login/role change/delete)
  - `@audit_log(action="user.suspend")` 데코레이터 패턴
  - before/after JSONB 자동 캡처 (변경 전후 모델 dict)
  - 비동기 INSERT (메인 요청 블로킹 방지)
- **적용 대상 (OQ-10 권장)**:
  - admin endpoints: `PATCH /admin/users/{id}`, `POST /admin/featured-artist/{id}/approve`, `POST /admin/collections/{id}/approve` 등 주요 10~15개
  - sensitive user: POST /auth/admin/login (실패 포함), POST /admin/users/{id}/role-change
- **보존 기간** (OQ-4 권장: 1년):
  - `audit_logs` 1년 보존 정책 (한국 개인정보보호법 7년 미만, 운영 이력 충분)
  - cron cleanup 또는 DB partitioning (Phase 12에서 결정)
  - `docs/runbook/audit-logs-retention.md` 정책 문서 작성

**Acceptance Criteria**

- [ ] alembic 0084 적용 후 `audit_logs` 테이블 생성 확인 (down_revision: `0083_ai_collections`)
- [ ] audit_middleware 데코레이터 동작: admin 액션 → audit_logs INSERT 확인
- [ ] before_data / after_data JSONB 정상 기록 확인
- [ ] IP 주소 기록 확인
- [ ] 보존 정책 문서 (`docs/runbook/audit-logs-retention.md`) 작성 확인
- [ ] unit tests: `test_audit_middleware.py` (INSERT 동작 + 비동기 처리)

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 고빈도 admin 액션 시 INSERT 성능 | 낮음 | 비동기 task_queue 패턴으로 메인 요청 블로킹 방지 |
| JSONB before/after 크기 폭증 | 낮음 | 민감 필드(password_hash 등) 자동 마스킹 처리 |

**KPIs**

- admin 주요 액션 audit 커버리지: ≥ 15개 endpoint
- audit_logs 쿼리 응답: ≤ 100ms (인덱스 기준)

---

#### D-3: 가입 다양화 (이메일+비밀번호 우선)

**Feature ID**: `auth-email-password`
**우선순위**: Should (이메일+비밀번호 1순위, GitHub/매직링크 Phase 12 이월)
**Wave**: Wave D (D-1, D-2와 병행 가능)
**예상 기간**: ~10일
**의존성**: 없음 (독립)
**alembic**: **0085** (사용자 테이블 이메일 인증 컬럼 추가)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

user-system-guide gap 분석: 현재 가입 방법은 Google OAuth 1종뿐이다. README 비전("동유럽이든 남미든 동아시아든")의 글로벌 신진작가가 구글 계정 없이 가입할 수 없다. 이메일+비밀번호 기반 가입을 추가해 진입 장벽을 낮춘다. OQ-5 권장에 따라 GitHub OAuth와 매직링크는 Phase 12 이월.

**Scope**

- **alembic 0085: 사용자 테이블 확장**:
  - `users` 테이블에 컬럼 추가:
    - `password_hash VARCHAR(255)` (bcrypt, 이메일 가입자만 NULL 아님)
    - `email_verified BOOLEAN DEFAULT FALSE`
    - `email_verify_token VARCHAR(255)` (24h 유효)
    - `email_verify_expires_at TIMESTAMPTZ`
  - Google OAuth 가입자는 `email_verified=TRUE`, `password_hash=NULL`
- **이메일+비밀번호 회원가입 API**:
  - `POST /auth/register` → `{ email, password, display_name }` → 가입 + 인증 메일 발송
  - 비밀번호 정책: 최소 8자, 특수문자 1개 이상
  - `GET /auth/verify-email?token={token}` → 이메일 인증 완료
  - SES 인증 메일 (기존 SES 인프라 활용)
- **이메일+비밀번호 로그인 API**:
  - `POST /auth/login` → `{ email, password }` → JWT 발급
  - 5회 연속 실패 시 15분 잠금 (기존 admin 로그인 패턴 준용)
- **비밀번호 재설정**:
  - `POST /auth/password/reset-request` → 재설정 메일 발송
  - `POST /auth/password/reset` → `{ token, new_password }` → 비밀번호 변경
- **프론트엔드**:
  - 로그인 페이지: Google 버튼 + 이메일/비번 폼 병렬 표시
  - 회원가입 페이지: 이메일/비번 폼 + 이메일 인증 안내
  - "이메일 인증 필요" 배너 (미인증 사용자 대상)
  - 5 locale i18n 키: `auth.email_register.*`, `auth.login.*`

**Acceptance Criteria**

- [ ] alembic 0085 적용 후 `users` 테이블 신규 컬럼 확인 (down_revision: `0084_audit_logs`)
- [ ] `POST /auth/register` → 가입 + SES 인증 메일 발송 확인
- [ ] `GET /auth/verify-email?token` → 이메일 인증 완료 확인
- [ ] `POST /auth/login` → JWT 발급 확인
- [ ] 5회 실패 → 15분 잠금 확인
- [ ] 비밀번호 재설정 플로우 end-to-end 확인
- [ ] 로그인 페이지 Google + 이메일 폼 병렬 표시 확인
- [ ] unit tests: `test_email_auth.py` + integration tests: `test_auth_flow.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 이메일 인증 미완료 사용자 UX | 중간 | 미인증 배너 + 기능 제한 없음 (단계적 접근) |
| bcrypt 해시 성능 | 낮음 | bcrypt cost=12 (Phase 8 admin 패턴 준용) |
| Google OAuth와 이메일 계정 중복 이메일 처리 | 높음 | 동일 이메일 → 기존 Google 계정으로 통합 안내 |

**KPIs**

- 이메일+비밀번호 가입 완료율: ≥ 80% (이메일 인증 포함)
- 이메일 인증 메일 발송 성공율: ≥ 95%
- 인증 완료율 (메일 발송 → 인증 클릭): baseline 측정 시작

---

## 5. Open Questions (OQ 목록)

사용자가 "권장대로" 한 번에 수락 가능하도록 권장 default를 명시한다.

| # | Open Question | 권장 Default | 근거 |
|:-:|---------------|:------------|------|
| **OQ-1** | C-1 K-6 진입 조건 거래 ≥ 100건 재확인 시점 | **Wave A 시작 전 즉시 카운트 확인 후 결정** | Phase 10 이후 K-2 Diversity + K-4 Featured Artist 효과로 거래 증가 가능 |
| **OQ-2** | B-1 Admin 실험 결과 시각화 방식 | **PostHog Insights 임베드 (개발 비용 ↓)** | 별도 차트 라이브러리 도입 불필요. CSP 이슈 시 API fetch + 자체 차트 fallback |
| **OQ-3** | D-1 단축키 우선 구현 목록 | **j/k 피드 네비게이션 + ⌘S 임시저장 + ? 도움말 (3+1개 우선)** | 가장 빈번한 동작 + 도움말은 확장성 위해 필수 |
| **OQ-4** | D-2 audit_logs 보존 기간 | **1년** | 한국 개인정보보호법 준수(7년 미만), 운영 이력 추적 충분 |
| **OQ-5** | D-3 가입 다양화 우선 순서 | **이메일+비밀번호 1순위, GitHub OAuth + 매직링크는 Phase 12 이월** | 이메일 가입은 구글 계정 없는 신흥 시장 최우선 요구 |
| **OQ-6** | A-1/A-2 Admin 큐 autopublish 정책 | **검수 후 publish (autopublish OFF 유지)** | Phase 10 K-4/K-7 설계 의도 유지, ML 스코어 어뷰징 방지 |
| **OQ-7** | B-2 Diversity 변경 적용 시점 | **Redis 5분 캐시 자연 만료 (현재 동작 유지, 즉시 강제 갱신 불필요)** | 현재 K-2 서비스 동작과 일치, 강제 캐시 무효화 구현 생략 |
| **OQ-8** | C-1 AI 가격 추천 알고리즘 | **단순 비교 작품 평균가 + 작가 작품 평균가 가중 (0.4:0.6)** | ML 회귀는 Phase 12 검토. 거래 100건 수준에서는 단순 중앙값이 더 안정적 |
| **OQ-9** | D-1 단축키 도움말 표시 키 | **`?` (GitHub/Slack 표준)** | 사용자 기대 부합, 기존 단축키와 충돌 없음 |
| **OQ-10** | D-2 audit middleware 적용 범위 | **admin endpoints (15개) + sensitive user actions (login 실패, role change, delete)** | 운영 필수 추적 + 개인정보 규정 준수 범위 |
| **OQ-11** | Wave 진입 순서 | **A 완료 후 B 진입. B와 Wave D 병행. C는 거래 100건+ 충족 시만** | A는 운영 차단 요소 → 최우선. D는 독립적이므로 B와 병행 가능 |
| **OQ-12** | Phase 11 종결 시점 | **6~8주 (Wave A 3주 + Wave B 3주 + Wave D 병행 2주, C는 조건부 추가 2주)** | Phase 10 타임라인 패턴 준용 |
| **OQ-13** | D-3 Google 계정과 이메일 중복 처리 | **동일 이메일 → 기존 Google 계정으로 통합 안내 (별도 계정 생성 불가)** | 계정 분리 시 혼란 방지, 소셜 연동 확장 대비 |

---

## 6. Wave 병렬 위임 전략

```
Phase 11 시작 전 (Day 0)
  ├── [사전 확인] auctions.status='sold' 카운트 → C-1 진입 여부 즉시 결정 (OQ-1)
  └── [환경 확인] alembic head = 0083_ai_collections 확인

Wave A (Week 1~3, 2 agents 병렬)
  ├── [Agent 1: frontend-architect] A-1 /admin/featured-artist/queue UI (K-4 검수 큐)
  └── [Agent 2: frontend-architect] A-2 /admin/ai-collections/queue UI (K-7 검수 큐)

Wave D (Week 2~4, 최대 3 agents, Wave A 완료 후 또는 Wave A와 일부 병행)
  ├── [Agent 1: frontend-architect] D-1 키보드 단축키 (useGlobalHotkeys + 도움말 모달)
  ├── [Agent 2: bkend-expert] D-2 audit_logs DB (alembic 0084 + middleware)
  └── [Agent 3: bkend-expert + frontend-architect] D-3 이메일+비밀번호 가입 (alembic 0085)

↓ (Wave A 완료 확인, ~Week 3)

Wave B (Week 3~6, 2 agents 병렬)
  ├── [Agent 1: frontend-architect] B-1 /admin/experiments UI (K-8 A/B 결과 분석)
  └── [Agent 2: frontend-architect] B-2 /admin/diversity-config UI (K-2 튜닝)

↓ (C-1 진입 조건 충족 시)

Wave C (Week 6~8, 조건부, 1 agent)
  └── [Agent 1: bkend-expert + frontend-architect] C-1 K-6 AI 가격 추천 (alembic 0086)
  └── [조건 미달 시] Phase 11 report에 명시 → Phase 12 이월
```

**병렬화 효율 예상**:
- Wave A 2 agents 병렬: A-1(10일) + A-2(10일) = 10일 (순차 20일 대비 50% 단축)
- Wave D 3 agents 병렬: D-1(7일) + D-2(7일) + D-3(10일) = 10일 (순차 24일 대비 58% 단축)
- Wave B 2 agents 병렬: B-1(10일) + B-2(7일) = 10일 (순차 17일 대비 41% 단축)
- Wave D와 Wave A/B 병행: Wave D 추가 오버헤드 없음 (독립적)

---

## 7. KPI 정의 (Phase 11 종결 시 측정)

### 7.1 Wave별 KPI 집계 기준

| sub-PDCA | 핵심 KPI | 목표값 | 측정 도구 |
|:--------:|---------|:------:|----------|
| **A-1** | K-4 Admin 큐 수동 DB 조작 건수 | 0건/주 (UI 전환 후) | Admin 운영 기록 |
| **A-1** | Featured Artist 검수 리드타임 | ≤ 48h | Admin 큐 created_at → reviewed_at |
| **A-2** | K-7 Admin 큐 수동 DB 조작 건수 | 0건/주 (UI 전환 후) | Admin 운영 기록 |
| **A-2** | 컬렉션 admin 승인율 | ≥ 70% | DB 쿼리 |
| **B-1** | ML 피드 v2 rollout 결정 완료 | Phase 11 내 결정 | Admin 설정 변경 기록 |
| **B-1** | A/B 결과 확인 리드타임 | ≤ 30초 (콘솔 내) | UI 성능 측정 |
| **B-2** | Diversity 파라미터 튜닝 리드타임 | curl(10분) → UI(2분) | 운영 기록 |
| **C-1** | 가격 추천 사용률 | ≥ 50% (조건 충족 시) | PostHog |
| **C-1** | 추천가 적용률 | ≥ 30% | PostHog |
| **D-1** | 단축키 구현 일치율 | 4/4 (우선 구현분) | 구현 체크리스트 |
| **D-2** | audit 커버리지 | ≥ 15개 admin endpoint | 코드 검토 |
| **D-3** | 이메일 가입 완료율 | ≥ 80% | 가입 funnel |
| **D-3** | 인증 메일 발송 성공율 | ≥ 95% | SES 로그 |

### 7.2 통합 KPI (Phase 11 종결)

| 지표 | 목표 | 비고 |
|------|:----:|------|
| Admin 콘솔 누락 메뉴 해소율 | 4/7 (Wave A+B 4개, Wave C+D 제외) | `/admin/analytics`, `/admin/payouts`, `/admin/system`은 Phase 12 |
| ML 피드 v2 rollout 결정 | 결정 완료 (B-1 결과 기반) | B-1 완료 후 양호/부진 판단 |
| 가입 방법 다양화 | 2종 (Google + 이메일+비밀번호) | D-3 완료 후 |
| Tests 총 수 | 646 → 700+ | 신규 +54 이상 목표 |
| alembic head | single head (0085 또는 0086) | D-2 0084, D-3 0085, C-1 0086 |
| tsc errors | 0 | A-1/A-2/B-1/B-2/D-1/D-3 모두 |

---

## 8. Risks & Mitigation

| 리스크 | 영향 | 가능성 | 대응 |
|--------|:----:|:------:|------|
| **Admin 콘솔 라우팅 패턴 불일치** | 중간 | 중간 | A-1/A-2/B-1/B-2 구현 전 `AdminShell.tsx` 기존 패턴 전수 분석 |
| **K-6 거래 100건 미달 지속** | 중간 | 높음 | OQ-1 기준: Phase 11 시작 즉시 카운트 확인, 미달 시 Wave C 없이 Phase 11 종결 (Wave A+B+D만으로 완성) |
| **D-3 Google 계정 중복 이메일 처리** | 높음 | 중간 | 동일 이메일 가입 시도 → 기존 Google 계정 안내. 계정 합병 로직은 Phase 12 |
| **audit_logs INSERT 성능 (D-2)** | 낮음 | 낮음 | 비동기 background task 패턴, 메인 요청 블로킹 없음 |
| **Wave A/B Frontend 전용 → Backend 변경 발생** | 낮음 | 낮음 | Backend API는 Phase 10에서 완성됨. 신규 backend 작업 없음 (D-2, D-3 제외) |
| **D-1 단축키 접근성 충돌** | 낮음 | 낮음 | `j/k`는 AT(보조기술) 비충돌. `?`는 ARIA landmark와 무관. Esc는 FocusManager 우선순위 정의 |
| **alembic 0084-0086 충돌** | 중간 | 낮음 | 사전 배정 순서 준수: D-2(0084) → D-3(0085) → C-1(0086). Wave D 완료 후 순차 merge |

---

## 9. alembic Migration Chain

| revision | sub-PDCA | 테이블 | down_revision |
|----------|:--------:|--------|:-------------:|
| `0083_ai_collections` | K-7 (Phase 10) | `ai_collections`, `ai_collection_posts` | `0082_featured_artist_candidates` |
| **`0084_audit_logs`** | **D-2** | `audit_logs` | `0083_ai_collections` |
| **`0085_email_auth`** | **D-3** | `users` +4 컬럼 (password_hash, email_verified, email_verify_token, email_verify_expires_at) | `0084_audit_logs` |
| `0086_*` (조건부) | C-1 K-6 진입 시 | 가격 추천 로그 (선택) 또는 없음 | `0085_email_auth` |

> **충돌 방지 원칙**:
> - A-1, A-2, B-1, B-2, D-1: 프론트엔드 전용 — alembic 작업 없음
> - D-2 (0084) → D-3 (0085) → C-1 (0086) 순서로 단계적 merge
> - Phase 11 종결 목표: **single head `0085_email_auth`** (C-1 미진입 시) 또는 **`0086_*`** (C-1 진입 시)

---

## 10. Phase 12 검토 후보

Phase 11 종결 후 운영 데이터 기반으로 우선순위 재평가.

| 후보 | 조건/근거 | 예상 우선순위 |
|------|----------|:------------:|
| **K-6 AI 가격 추천 (C-1 미진입 시)** | 거래 100건 미달 시 Phase 11 → 12 이월 | Must (이월) |
| **GitHub OAuth + 매직링크 가입** | D-3 이메일 가입 완료 후 자연스러운 확장 | Should |
| **`/admin/analytics` 통합 대시보드** | 운영 데이터 증가 후 필요성 증대. 백엔드 일부 구현 필요 | Should |
| **`/admin/payouts` 정산 관리 UI** | settlement_jobs.py 백엔드 완성 후 UI 구현 | Should |
| **`/admin/system` cron 모니터** | 백엔드 미구현 → Phase 12에서 설계부터 시작 | Could |
| **ML 모델 재학습 자동화** | K-8 A/B 결과 기반 자동 재학습 트리거 정교화 | Should |
| **K-6 ML 회귀 모델** | 거래 500건+ 이상 축적 후 단순 중앙값 → ML 회귀 전환 | Could |
| **전역 단축키 확장** | D-1 기반 `g h`, `n`, `/`, `l`, `b` 등 추가 구현 | Should |
| **audit_logs 파티셔닝** | D-2 기반, 데이터 증가 후 created_at 기준 파티션 전환 | Could |
| **모바일 Native (iOS/Android)** | README "주머니 앱" — 현재 web only (Phase 10 report 옵션 B) | Should (Phase 12+) |

---

## 11. Phase 11 타임라인 (예상)

| 기간 | 활동 | sub-PDCA | 상태 |
|:---:|------|:--------:|:----:|
| Day 0 | 거래 카운트 확인 → C-1 진입 여부 결정 + alembic head 확인 | 사전 준비 | ⏳ |
| W1 | A-1 Admin 특산 Artist 큐 UI 설계 + 구현 시작 | A-1 | ⏳ |
| W1 | A-2 Admin AI 컬렉션 큐 UI 설계 + 구현 시작 (A-1 병렬) | A-2 | ⏳ |
| W1~2 | D-2 audit_logs alembic 0084 + middleware 시작 (Wave A 병행) | D-2 | ⏳ |
| W2 | A-1 완료 + A-2 완료 검토 | Wave A | ⏳ |
| W2~3 | D-1 useGlobalHotkeys hook + 도움말 모달 | D-1 | ⏳ |
| W2~3 | D-3 이메일+비밀번호 가입 alembic 0085 + API + UI | D-3 | ⏳ |
| W3 | D-2 완료 + D-1 완료 + D-3 완료 | Wave D | ⏳ |
| W3~4 | B-1 Admin 실험 결과 UI 설계 + 구현 | B-1 | ⏳ |
| W3~4 | B-2 Admin Diversity 튜닝 UI 설계 + 구현 (B-1 병렬) | B-2 | ⏳ |
| W4~5 | B-1 완료 + B-2 완료 검토 | Wave B | ⏳ |
| W5 | B-1 결과 기반 ML_FEED_DEFAULT_ALGO rollout 결정 | ML rollout | ⏳ |
| W5~6 | C-1 진입 조건 충족 시: K-6 AI 가격 추천 설계 + 구현 | C-1 | ⏳ |
| W6~8 | C-1 완료 (조건 충족 시) 또는 Phase 11 종결 (미충족 시) | C-1 / 종결 | ⏳ |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 1.0 | 2026-05-08 | Phase 11 초안 (8 sub-PDCAs, OQ 13개, alembic 0084~0086 사전 배정) | itpe-ince (Claude Sonnet 4.6) |
