---
template: plan
version: 1.0
feature: domo-phase10-roadmap
date: 2026-05-06
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 10 (K Wave 2: ML 고도화 + Phase 9 Carry-over 청산)
status: Draft (Roadmap)
---

# Domo Phase 10 — 로드맵 (Master Plan)

> **Summary**: Phase 9 종결(L 6 + K Wave 1 3 = 9 sub-PDCA, 93.0% 가중 Match Rate, 2026-05-06) 후 K Wave 2를 순차/병렬 진행한다. **사용자 옵션 A 수락**: K-1 운영 14일 후 K-8 A/B 측정 인프라 + K-2 Diversity Reranking 즉시 진입(Wave A), K-4 Featured Artist 자동화 + K-7 Editor's Pick 컬렉션(Wave B), K-6 AI 가격 추천(Wave C, 조건부), CO-1 Phase 9 Carry-over 11항목 청산(Wave D 병행). 총 6 sub-PDCAs, 6~8주 예상. Critical Path: H'-6 → L-A → K-1 → K-2 완성.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-06
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 10 배경 & 전략적 의미

### Phase 9 종결 성과

Phase 9는 L 단계(L-A~L-F 6개) + K Wave 1(K-1/K-3/K-5 3개) = 9 sub-PDCA 100% 종결(2026-05-06). 주요 성과:

- **Critical Path 완성**: H'-6(50K behavioral events) → L-A(pgvector 임베딩) → K-1(Collaborative Filtering 피드 v2) 사슬 완성
- **AI 스토리텔링 허브**: K-3 AI 작품 캡션 + K-5 LLM 도슨트로 5 locale 자동화. translation_cache 재사용으로 비용 최소화
- **누적 지표**: 테스트 510 → 581 (+71), alembic 0066~0079 (14 마이그레이션, single head `0079_llm_docent`), cron 16 → 21 (+5)
- **Phase 9 전체 가중 Match Rate**: K Wave 1 95.1%, Phase 9 전체 93.0% — iterate 불필요

### Phase 10가 중요한 이유

K-1은 출시됐지만 **운영 데이터 없이는 ML 모델 가치를 검증할 수 없다**. Phase 10는 두 가지 목표를 동시 달성한다:

**1. K Wave 2 — 운영 데이터 기반 ML 고도화**: K-1 운영 14일 후 실제 CTR/engagement 데이터를 수집해 K-8 A/B 테스트로 v1 vs v2 효과를 측정하고, K-2 Diversity Reranking으로 필터 버블을 방지한다. K-4 Featured Artist 자동화와 K-7 Editor's Pick은 운영 임베딩을 기반으로 한 다음 단계 큐레이션이다.

**2. CO-1 — Phase 9 Carry-over 완전 청산**: K Wave 1 분석에서 식별된 11개 잔존 항목(기술 부채 + 미완 UI + CI 개선)을 단일 sub-PDCA로 청산. 향후 Phase에서 기술 부채 누적 방지.

```
[Phase 9 L] Carry-over Consolidation + pgvector 임베딩 인프라
    ↓
[Phase 9 K Wave 1] K-1(ML 피드) + K-3(AI 캡션) + K-5(LLM 도슨트)
    ↓
[Phase 10 Wave A] K-8(A/B 측정 인프라) + K-2(Diversity Reranking) — K-1 운영 데이터 활용
    ↓
[Phase 10 Wave B] K-4(Featured Artist 자동화) + K-7(Editor's Pick) — 임베딩 기반 확장
    ↓
[Phase 10 Wave C] K-6(AI 가격 추천) — 조건부 (거래 ≥ 100건)
    ↓ (병행)
[Phase 10 Wave D] CO-1(Carry-over 11항목 청산) — Wave A와 병행 시작
```

---

## 1. 비즈니스 컨텍스트

### Phase 9 → Phase 10 전환

Phase 9에서 "AI가 작품을 설명한다"면, Phase 10는 "AI가 올바른 작품을 올바른 사람에게 추천하고, 그 효과를 측정한다"는 단계다.

```
Phase 9까지의 Domo: AI가 작품 캡션/도슨트를 생성 → 콘텐츠 품질 자동 증폭 (공급 측)
Phase 10의 Domo: ML이 최적 콘텐츠를 최적 사용자에게 추천 → 매칭 효율 측정 (수요-공급 연결)
```

### ML 고도화가 README 비전을 완성하는 이유

| README 비전 | Phase 9 달성 | Phase 10 달성 |
|-------------|:----------:|:----------:|
| "유저들이 늘어나야 소비자들도 늘어남" | K-1 ML 피드 v2 출시 ✅ | K-8 A/B로 CTR 효과 측정 → K-2로 필터 버블 방지 → 더 많은 신규 발굴 |
| "전 세계 아티스트들의 인덱스" | K-1 Collaborative Filtering ✅ | K-2 신진작가 부스팅 + K-4 Featured Artist 자동화 → 글로벌 인덱스 능동 큐레이션 |
| "AI 시대 작가의 정체성 재정의" | K-3 캡션 + K-5 도슨트 ✅ | K-7 Editor's Pick으로 작가 발견 가속 → K-6 가격 추천으로 진입장벽 ↓ |
| "컬렉터들한테는 회비" | K-3/K-5 스토리텔링 ✅ | K-7 컬렉션으로 컬렉터 탐색 경험 풍부화 → 구독 가치 증가 |
| "신진작가 거래 이루어지고 인덱스 만들고" | K-1 ML 스코어 ✅ | K-6 AI 가격 추천으로 reserve_price 설정 불안 해소 → 경매 낙찰률 ↑ |

### 운영 데이터 준비 상태 (Phase 10 ML 진입 조건)

K-1 출시 후 14일 운영이 Phase 10 Wave A의 선행 조건이다:

- **ml_experiments 기반 A/B 분기**: K-8에서 PostHog Feature Flag `ml_feed_v2` 50:50 분배 → 14일 데이터 축적
- **user_post_interactions 누적**: K-1 interaction 기록 → Precision@10 측정 가능
- **L-B newsletter_events + open rate**: K-8 측정 지표 통합 활용

---

## 2. Phase 9 결과 → Phase 10 매핑

| Phase 9 산출물 | Phase 10 활용 | sub-PDCA |
|--------------|:------------|:--------:|
| K-1 `user_post_interactions` (alembic 0073) | K-8 A/B 분기 소스 + K-2 reranking 입력 | K-8, K-2 |
| L-A `user_embeddings` + `post_embeddings` | K-4 Featured Artist 스코어링 + K-6 유사 작품 탐색 | K-4, K-6 |
| L-A pgvector ivfflat index | K-7 K-means 클러스터링 주제 발견 | K-7 |
| L-F `translation_cache` | K-7 컬렉션 제목/설명 자동 번역 (비용 ↓) | K-7 |
| Phase 6 `artist_index` (Redis + DB) | K-2 신진작가 부스팅 스코어 소스 | K-2 |
| Phase 7 G'-7 admin featured manual | K-4 admin 검수 큐 패턴 계승 | K-4 |
| K-3 `ai_caption` 필드 (alembic 0078) | K-7 클러스터링 텍스트 feature | K-7 |
| L-B newsletter open rate | K-8 측정 지표 통합 (engagement signal) | K-8 |
| K-wave1 gap: K-3 rate limit 미구현 | CO-1 rate limit 3회/일 명시 추가 | CO-1 |
| K-wave1 gap: FeedAlgo "v2" 타입 누락 | CO-1 TypeScript 타입 보강 | CO-1 |
| K-wave1 gap: FeedItem/GalleryView alt 미완 | CO-1 `<img>` alt sweep 전체 완료 | CO-1 |
| K-wave1 gap: 작가 편집 도슨트 UI 미관찰 | CO-1 도슨트 폼 + opt-out 토글 UI 추가 | CO-1 |
| L-D 3 skipped tests 사유 미문서화 | CO-1 `docs/TESTING_NOTES.md` 작성 | CO-1 |
| i18n 키 자동 검증 미구축 | CO-1 CI jq/Node 스크립트 도입 | CO-1 |

---

## 3. README 비전 직접 매핑

> README 원문 직접 인용 → Phase 10 구현 매핑

| README 원문 | Phase 10 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| **"유저들이 늘어나야 소비자들도 늘어남 — 그로스해킹"** | **K-8** | PostHog Feature Flag A/B 테스트로 ML 피드 CTR 효과 측정. CTR ↑ → 사용자 유입 증가 → 후원자 전환율 측정 가능 |
| **"전 세계 아티스트들의 인덱스를 만들고 싶음"** | **K-2, K-4** | Diversity Reranking(K-2)으로 필터 버블 방지 → 신진작가 발굴 자동화. Featured Artist(K-4)로 주간 글로벌 신진작가 자동 인덱싱 |
| **"동유럽이든 남미든 동아시아든 — 꿈과 희망"** | **K-2, K-4** | 지역 다양성 ≥ 2종 제약(K-2)으로 지역 편중 방지. K-4 다양성 보정(10%) → 지역 언더-represented 신진작가 자동 부스팅 |
| **"컬렉터들한테는 회비 1년에 10분씩"** | **K-7** | Editor's Pick 주제별 컬렉션 → 컬렉터 탐색 경험 풍부화. 주간 컬렉션 자동 생성으로 구독 유지 가치 증가 |
| **"신진 작가들의 거래 이루어지면 인덱스 만들고"** | **K-6** | AI 가격 추천으로 reserve_price 설정 불안 해소 → 경매 낙찰률 ↑ → 실제 거래 데이터 축적 → 인덱스 정교화 |
| **"히스토리를 두세 개 만든다"** | **K-7** | AI 큐레이션 컬렉션 제목/설명 자동 생성 → 언론/SNS 확산 가능한 "발견 스토리" 자동화 |
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | **K-6** | AI 가격 추천으로 신진작가 경매 진입장벽 ↓. 적정 가격 책정 → 낙찰 성공 → 생존 가능성 ↑ |

---

## 4. Sub-PDCA 상세 (6개)

### Wave A — K-1 운영과 병행 측정 (즉시 진입, 2 agents 병렬)

---

#### K-8: ML A/B 테스트 (PostHog Feature Flag + 운영 측정 인프라)

**Feature ID**: `ml-ab-test-infra`
**우선순위**: Must (Critical — 운영 측정 인프라)
**Wave**: Wave A (즉시 진입)
**예상 기간**: ~7일
**의존성**: K-1 운영 14일 데이터 (선행 조건)
**Booster 관계**: K-1 (`user_post_interactions`), L-B (`newsletter_events` open rate), Phase 8 B'-5 (PostHog analytics dashboard), G''-1 (OTel trace_id)
**alembic**: **0080** (`ml_experiments` + `ml_experiment_assignments`)
**담당 agent**: bkend-expert

**Goal**

K-1 ML 피드 v2와 기존 룰 기반 피드 v1의 성능을 PostHog Feature Flag 기반 A/B 테스트로 비교한다. Feed CTR, Precision@10, Session duration, 후원 전환율을 14일 이상 측정해 ML 피드 v2의 비즈니스 가치를 통계적으로 검증한다.

**Scope**

- **PostHog Feature Flag A/B 분기**:
  - Flag name: `ml_feed_v2` (OQ-1 권장: 50:50 균등 분배)
  - 대조군(v1): 기존 feed_scoring_jobs 룰 기반
  - 실험군(v2): K-1 Collaborative Filtering ML 피드
  - Flag 기반 분기 로직: `_resolve_ml_algo(algo, user)` 확장
- **alembic 0080: ml_experiments + ml_experiment_assignments**:
  - `ml_experiments`: experiment_id, name, flag_key, started_at, ended_at, status ENUM (running/paused/completed)
  - `ml_experiment_assignments`: assignment_id, experiment_id FK, user_id FK, variant (control/treatment), assigned_at
  - 인덱스: user_id + experiment_id (UNIQUE), experiment_id + assigned_at DESC
- **측정 KPI**:
  - Feed CTR (PostHog capture event: `feed_post_click`)
  - Precision@10 (일일 ml_model_metrics 기록)
  - Session duration (PostHog session duration)
  - 후원 전환율 (PostHog event: `sponsor_created` funnel)
  - L-B newsletter open rate 통합 (engagement signal 보조)
- **모니터링 대시보드**:
  - PostHog Experiment 결과 자동 계산 (내장 통계 검정, OQ-10 권장)
  - Prometheus metric: `ml_ab_test_assignments_total`, `ml_ab_test_conversions_total`
  - 통계적 유의성 p < 0.05 달성 시 자동 슬랙 알림 (L-F 패턴 재사용)

**Acceptance Criteria**

- [ ] alembic 0080 적용 후 `ml_experiments` + `ml_experiment_assignments` 테이블 생성 확인
- [ ] PostHog Feature Flag `ml_feed_v2` 생성 + 50:50 rollout 동작 확인
- [ ] `GET /api/feed?algo=auto` → Feature Flag 기반 v1/v2 분기 정상 동작
- [ ] ml_experiment_assignments 레코드 생성 (사용자별 variant 기록)
- [ ] PostHog Experiment 대시보드에서 CTR, Session duration 실시간 확인
- [ ] 14일 후 통계적 유의성 p < 0.05 기준 보고 준비
- [ ] Prometheus `ml_ab_test_assignments_total` metric 수집 확인
- [ ] unit tests: `test_ml_ab_test.py` + integration tests: `test_feed_ab_api.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 소규모 사용자 수에서 통계적 유의성 부족 | 높음 | Bayesian A/B 방법 + 14일 이상 연장 (OQ-2 권장: 14일) |
| Feature Flag 분배 불균형 | 중간 | PostHog 내장 균형 분배 + ml_experiment_assignments 비율 모니터링 |
| newsletter open rate 신호 잡음 | 낮음 | 보조 지표로만 활용, 주지표는 Feed CTR |

**KPIs**

- A/B 테스트 통계적 유의성: p < 0.05 (14일 이상 운영 후)
- 피드 v2 CTR: v1 대비 ≥ 15% 향상 (실험군)
- Session duration: v1 대비 ≥ 10% 향상
- 후원 전환율 baseline: 측정 시작 (절대값보다 v1 vs v2 delta가 목표)

---

#### K-2: Diversity Reranking (필터 버블 방지 + 신진작가 부스팅)

**Feature ID**: `feed-diversity-reranking`
**우선순위**: Must
**Wave**: Wave A (즉시 진입, K-8과 병렬)
**예상 기간**: ~7일
**의존성**: K-1 (ML 피드 v2 완성, 14일 운영 데이터 활용)
**Booster 관계**: K-1 (ML 스코어), Phase 6 `artist_index` (genre/region tag + 신진작가 랭킹), K-8 (A/B 측정으로 reranking 효과 검증)
**alembic**: **0081** (`diversity_constraints` config table 또는 env 기반, OQ-3 권장: env 기반 + 0081 config table 병용)
**담당 agent**: bkend-expert

**Goal**

K-1 ML 피드가 특정 장르/지역 작가에 편중되는 필터 버블 현상을 방지한다. 14일 운영 데이터에서 장르/지역 편중 패턴을 분석한 뒤, 다양성 제약(장르 ≥ 3종, 지역 ≥ 2종)과 신진작가 +20% 부스팅을 적용한다.

**Scope**

- **14일 운영 데이터 분석**:
  - K-1 피드 결과의 장르/지역 분포 히트맵 계산
  - artist_index 기반 신진작가(팔로워 < 100, 포스트 수 < 10) 노출 비율 측정
  - 편중도 임계값 결정 → K-2 가중치 보정값 도출 (OQ-3 권장값 적용)
- **alembic 0081: diversity_constraints**:
  - `diversity_constraints`: constraint_id, name, genre_min_count, region_min_count, newcomer_boost_pct, lambda_weight, is_active, updated_at
  - 초기값: genre_min_count=3, region_min_count=2, newcomer_boost_pct=20, lambda_weight=0.30
- **Diversity Reranking 서비스**:
  - `app/services/diversity_reranker.py` 신규
  - 입력: K-1 ML 스코어 상위 50개 후보
  - MMR(Maximal Marginal Relevance) 알고리즘 적용:
    - 장르 제약: 상위 20개 중 동일 장르 ≤ 6개 (30%)
    - 지역 제약: 상위 20개 중 동일 국가/지역 ≤ 8개 (40%)
    - 신진작가 부스팅: artist_index 기반 `+20%` 스코어 가산
  - `GET /api/feed?algo=v2` → ml_feed_inference → diversity_reranker 순차 적용
- **신진작가 배지 UI**:
  - "Domo Discovery" 배지 (PostCard 컴포넌트) — 팔로워 < 100 신진작가 식별
  - 5 locale i18n 키: `feed.discovery_badge` (ko/en/ja/zh/es)
- **가중치 튜닝 주기** (OQ-12 권장: 월 1회):
  - diversity_constraints admin 편집 API: `PATCH /api/admin/diversity-constraints/{id}`

**Acceptance Criteria**

- [ ] alembic 0081 적용 후 `diversity_constraints` 테이블 생성 + 초기값 seed
- [ ] `diversity_reranker.py` — 상위 50개 후보 → 장르 ≥ 3종, 지역 ≥ 2종 제약 적용 확인
- [ ] 신진작가(팔로워 < 100) +20% 부스팅 → 피드 노출율 ≥ 30% 증가 확인
- [ ] "Domo Discovery" 배지 5 locale UI 표시 확인
- [ ] Reranking 후 ML 추천 품질(NDCG@10) 저하 ≤ 5% 허용 (A/B K-8 측정)
- [ ] `PATCH /api/admin/diversity-constraints/{id}` 동작 확인 (가중치 실시간 조정)
- [ ] unit tests: `test_diversity_reranker.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 다양성 가중치 과다 → 개인화 품질 저하 | 높음 | 초기값 보수적(lambda=0.30), K-8 A/B로 최적값 탐색 |
| 장르 태그 누락 포스트 처리 | 중간 | genre=null → "미분류" 버킷 별도 처리 |
| Cold start 사용자에서 reranking 무의미 | 낮음 | Chronological fallback 사용자는 reranking 미적용 (OQ-11 권장: 기존 fallback 유지) |

**KPIs**

- 장르 다양성 지수: 상위 20 피드 중 ≥ 3개 장르 (Shannon entropy ≥ 1.5)
- 신진작가 발굴율: 주간 피드에서 팔로워 < 100 작가 노출 ≥ 30%
- Reranking 처리 시간: ≤ 20ms (추가 레이턴시)

---

### Wave B — Wave A 완료 약 2주 후 (2 agents 병렬)

---

#### K-4: AI Featured Artist 자동 추천

**Feature ID**: `ai-featured-artist`
**우선순위**: Should
**Wave**: Wave B (Wave A 완료 후, 약 2주 후)
**예상 기간**: ~7일
**의존성**: L-A `user_embeddings` (필수), K-8 PostHog Feature Flag 인프라 (권장)
**Booster 관계**: Phase 7 G'-7 (admin manual featured 패턴 계승), L-A (임베딩), Phase 6 `artist_index` (랭킹), L-F Cohort alert (슬랙 알림 패턴)
**alembic**: **0082** (`featured_artist_candidates` 또는 기존 G''-7 테이블 확장, OQ-4 권장: 신규 0082)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 7 G'-7에서 admin이 수동으로 Featured Artist를 선정하던 것을 ML 알고리즘 자동 추천으로 전환한다. L-A user_embeddings + post_engagement_cache 활용해 매주 자동으로 "주간 추천 신진작가"를 선정하고, admin 검수 후 홈/피드 상단에 노출한다.

**Scope**

- **Featured Artist 스코어링 알고리즘**:
  - 다음 가중합으로 주간 score 계산:
    - 최근 7일 팔로워 증가율 (40%) — artist_index booster
    - 포스트 engagement rate (like + comment + save / view) (30%) — user_post_interactions (K-1)
    - 신진작가 여부 (팔로워 < 1000, 가입 < 12개월) 부스팅 (20%)
    - 지역/장르 다양성 보정 (10%) — K-2 패턴 재사용
  - 최근 4주 내 선정 작가 제외 (반복 선정 방지)
  - 상위 3명 자동 선정 → admin 검수 큐
- **alembic 0082: featured_artist_candidates**:
  - `featured_artist_candidates`: candidate_id, user_id FK, week_start DATE, score FLOAT, score_breakdown JSONB, status ENUM (pending/approved/rejected), reviewed_at, reviewed_by FK
  - 인덱스: week_start + status, user_id + week_start (UNIQUE)
- **Cron**: `featured_artist_jobs.py` (R-5 격리, 매주 월요일 06:00 UTC)
  - `weekly_featured_scoring()` → top-3 candidates INSERT
  - admin 미검수 시 48h 후 슬랙 알림 (L-F 패턴)
- **Admin API**:
  - `GET /api/admin/featured-artists/candidates` (ML 추천 3명 + 스코어 이유 breakdown)
  - `POST /api/admin/featured-artists/{id}/approve` (OQ-4 권장: autopublish OFF)
  - `POST /api/admin/featured-artists/{id}/reject` + 사유 입력
- **프론트엔드 노출**:
  - 홈 상단 "이번 주 추천 신진작가" 섹션 (3명 카드)
  - 피드 중간 삽입 (10번째 포스트마다 Featured Artist 배너)
  - 5 locale i18n (`featured.weekly_rising`, `featured.this_week` 등)

**Acceptance Criteria**

- [ ] alembic 0082 적용 후 `featured_artist_candidates` 테이블 생성 확인
- [ ] `featured_artist_jobs.py` 주간 cron 동작 (22번째 worker, `FEATURED_ARTIST_WORKER_ENABLED` guard)
- [ ] 스코어 breakdown JSONB 정상 기록 (4개 가중치 분해 확인)
- [ ] admin 큐에서 승인/거부 API 동작 확인
- [ ] 홈 상단 + 피드 배너 5 locale 노출 확인
- [ ] 신진작가(팔로워 < 1000) 선정 비율 ≥ 70% 확인
- [ ] 최근 4주 내 선정 작가 제외 로직 동작 확인
- [ ] unit tests: `test_featured_artist_jobs.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| ML 스코어 조작 가능성 (어뷰징) | 높음 | admin 최종 승인 필수 (autopublish OFF 정책) |
| 동일 작가 반복 선정 | 중간 | 최근 4주 내 선정 작가 제외 규칙 (DB 쿼리) |
| 신진작가 부족 시 후보 부족 | 낮음 | 팔로워 < 1000 기준으로 완화 (K-2의 < 100과 차별화) |

**KPIs**

- Featured Artist 클릭률(CTR): ≥ 15% (홈 상단 카드 기준, PostHog)
- 신진작가 선정 비율: ≥ 70%
- 후원 전환율 (Featured → 후원): baseline 측정 시작

---

#### K-7: AI 큐레이션 컬렉션 (Editor's Pick 자동 생성)

**Feature ID**: `ai-curation-collection`
**우선순위**: Should
**Wave**: Wave B (K-4와 병렬)
**예상 기간**: ~7일
**의존성**: K-1 임베딩 (K-means 클러스터링), L-F `translation_cache` (제목/설명 번역), K-3 `ai_caption` (텍스트 feature)
**Booster 관계**: K-1 (ML 스코어 + pgvector), K-3 (ai_caption 텍스트), L-F (translation_cache 재사용), Phase 7 G'-7 (admin 검수 큐 패턴), L-B B'-3 (weekly digest email booster)
**alembic**: **0083** (`ai_collections` + `ai_collection_posts`)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

주제별 AI 큐레이션 컬렉션("Editor's Pick")을 주 1회 자동 생성해 컬렉터와 일반 관람자의 탐색 경험을 풍부하게 한다. LLM Gateway가 작품 메타 데이터(ai_caption + 장르 태그)를 분석해 컬렉션 제목/설명을 자동 생성한다.

**Scope**

- **컬렉션 자동 생성**:
  - 주제 클러스터링: pgvector K-means (k=5~8) → 주제 자동 발견
  - 클러스터 대표 포스트 10개 선정 (ML 스코어 상위 + diversity 보정)
  - tuzigroup LLM Gateway: 클러스터 대표 포스트 ai_caption → 컬렉션 제목 + 설명 자동 생성
  - `translation_cache` 재사용으로 5 locale 번역 비용 최소화 (OQ-6 권장: 일 $5 한도)
  - 이전 컬렉션 제목 목록 프롬프트 포함 → 클리셰 반복 방지
- **alembic 0083: ai_collections + ai_collection_posts**:
  - `ai_collections`: collection_id, title JSONB (5 locale), description JSONB (5 locale), theme_tag, cluster_k INT, generated_at, status ENUM (pending/approved/published/rejected), published_at, admin_note
  - `ai_collection_posts`: id, collection_id FK, post_id FK, rank INT, ml_score FLOAT
  - 인덱스: collection_id + status, generated_at DESC, post_id (중복 포함 가능)
- **Cron**: `ai_curation_jobs.py` (R-5 격리, 매주 월요일 09:00 UTC, OQ-5 권장)
  - `generate_weekly_collections()` → 3~5개 컬렉션 후보 생성 → admin 큐 INSERT
- **Admin API**:
  - `GET /api/admin/collections/pending`
  - `POST /api/admin/collections/{id}/approve`
  - `PATCH /api/admin/collections/{id}` (제목/설명 수동 편집)
  - `POST /api/admin/collections/{id}/reject`
- **프론트엔드 노출**:
  - `/explore` 페이지 — "이번 주 AI 큐레이션" 섹션
  - 컬렉션 상세 페이지 `/collections/{id}` — 포스트 그리드 (10개)
  - weekly digest email에 "추천 컬렉션" 섹션 추가 (L-B B'-3 booster)
  - 5 locale i18n (`collections.editors_pick`, `collections.this_week` 등)
- **LLM 비용 한도** (OQ-6 권장: 일 $5):
  - `AI_CURATION_DAILY_BUDGET_USD` 환경변수
  - translation_cache 캐시 히트율 ≥ 60% 목표로 비용 제어

**Acceptance Criteria**

- [ ] alembic 0083 적용 후 `ai_collections` + `ai_collection_posts` 테이블 생성 확인
- [ ] `ai_curation_jobs.py` 주간 cron 동작 (23번째 worker, `AI_CURATION_WORKER_ENABLED` guard)
- [ ] 컬렉션 제목/설명 JSONB 5 locale 모두 생성 확인
- [ ] admin 큐에서 승인/편집/거부 API 동작 확인
- [ ] `/explore` 페이지 + `/collections/{id}` 상세 페이지 5 locale 노출 확인
- [ ] weekly digest email 컬렉션 섹션 포함 확인 (L-B booster)
- [ ] LLM 일일 비용 $5 한도 guard 동작 확인
- [ ] unit tests: `test_ai_curation_jobs.py`

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 클러스터링 품질 저하 → 주제 없는 혼합 컬렉션 | 높음 | admin 큐 거부율 모니터링 + k값 자동 튜닝 |
| LLM 비용 폭증 | 높음 | 일 $5 한도 + translation_cache 재사용 (OQ-6) |
| LLM 제목 클리셰 반복 | 중간 | 이전 제목 목록 프롬프트 포함 → 다양성 주입 |

**KPIs**

- 컬렉션 admin 승인율: ≥ 70% (자동 생성 품질 기준)
- 컬렉션 페이지 CTR: ≥ 15% (`/explore` → 컬렉션 클릭)
- LLM 비용: 주당 $35 이하 (일 $5 × 7일)
- translation_cache 히트율: ≥ 60%

---

### Wave C — 조건부 진입 (거래 데이터 ≥ 100건)

---

#### K-6: AI 가격 추천 (경매 reserve_price)

**Feature ID**: `ai-price-recommendation`
**우선순위**: Should (조건부 — 거래 데이터 100건 미달 시 Phase 11 이월)
**Wave**: Wave C (거래 ≥ 100건 충족 시, OQ-7 권장: 100건)
**예상 기간**: ~7일
**진입 조건**: `auctions` 테이블 낙찰 완료(sold) 건수 ≥ 100건
**Booster 관계**: L-A `post_embeddings` (유사 작품 탐색), Phase 5 B-1 + Phase 6 A-6 (경매 DB 구조), K-1 (ML 스코어 가중치), K-8 (가격 추천 이벤트 PostHog 로깅)
**alembic**: 별도 maigration (번호 미사전배정, Wave C 진입 시 결정 — 0084 예약)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작가가 경매를 등록할 때 reserve_price(최저 낙찰가)를 설정하기 어려운 문제를 해결한다. 유사 작품 임베딩(L-A) + 과거 낙찰가 중앙값 + 장르별 시장 배수를 기반으로 추천 범위(min~max)를 제공한다.

**Scope**

- **진입 전 조건 확인**:
  - `SELECT COUNT(*) FROM auctions WHERE status = 'sold'` ≥ 100건
  - 미달 시: Phase 10 보고서에 "거래 데이터 부족 — Phase 11 이월" 명시
- **가격 추천 알고리즘**:
  - 유사 작품 탐색: `post_embeddings` pgvector cosine 유사도 top-5 (L-A booster)
  - 과거 낙찰가 중앙값 기반 추천가 산출
  - 장르별 시장 배수 (유화 1.8×, 수채화 1.2×, 디지털 아트 0.9×, 기타 1.0×)
  - 추천 범위: `[중앙값 × 0.8, 중앙값 × 1.3]` (신뢰구간 표시)
  - Fallback (거래 데이터 < 5건 장르): 장르 배수만 사용
- **API**:
  - `POST /api/auctions/price-recommend` (작품 ID + 장르 + 재료 → 추천 범위 반환)
  - 응답: `{ recommended_min, recommended_max, similar_auctions_count, confidence_level }`
  - 추천 이벤트 PostHog 로깅 (`auction_price_recommended`, `auction_price_applied`)
- **경매 등록 UI**:
  - reserve_price 입력 필드 옆 "AI 가격 추천" 버튼
  - 추천 범위 + 근거 ("유사 작품 N개 평균 낙찰가 기준") 표시
  - "추천가 적용" 버튼으로 자동 입력
  - 면책 문구: "이 추천은 참고용이며 실제 낙찰가를 보장하지 않습니다" (5 locale)

**Acceptance Criteria**

- [ ] 진입 조건(거래 ≥ 100건) 충족 확인 후 진행
- [ ] `POST /api/auctions/price-recommend` → 추천 범위 반환 (2초 내)
- [ ] 유사 작품 5개 이상 임베딩 유사도 기반 탐색 동작 확인
- [ ] 경매 등록 UI에서 추천 적용 버튼 동작 확인
- [ ] 면책 문구 5 locale 표시 확인
- [ ] PostHog `auction_price_recommended` 이벤트 로깅 확인 (K-8 연계)
- [ ] 거래 데이터 < 5건 장르 → fallback 장르 배수 모드 동작 확인

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| 거래 데이터 100건 미달 | 높음 | OQ-7 권장: Phase 11 이월 (강제 진행 금지) |
| 낮은 추천가 → 작가 수익 저해 | 중간 | "적정 범위" 명시 + 최저가 추천이 아님을 UI에 강조 |
| 가격 앵커링 효과 | 중간 | 추천가 제시 후 자유 입력 허용 (추천 ≠ 강제) |

**KPIs** (거래 100건+ 충족 시)

- 가격 추천 사용률: 경매 등록 시 ≥ 50% (버튼 클릭 기준)
- 추천가 적용률: ≥ 30% (추천 클릭 → "적용" 버튼 클릭)
- 낙찰 성공률 (reserve_price 사용 시): baseline 측정 시작

---

### Wave D — Phase 9 Carry-over 청산 (Wave A와 병행 시작)

---

#### CO-1: Phase 9 Carry-over 11항목 일괄 청산

**Feature ID**: `phase9-carryover-cleanup`
**우선순위**: Should
**Wave**: Wave D (Wave A와 병행 시작, 1~2주)
**예상 기간**: ~7~10일
**의존성**: 없음 (독립, Wave A와 병행 가능)
**담당 agent**: bkend-expert + frontend-architect (6 sub-task 분리 PR)

**Goal**

K Wave 1 Gap Analysis(K-wave1.analysis.md §5)에서 식별된 11개 잔존 항목을 단일 sub-PDCA로 청산한다. 6개 atomic PR로 분리해 독립 추적 가능하도록 한다 (OQ-8 권장).

**Carry-over 11항목 전체 목록**

| # | 항목 | 출처 | 우선순위 | sub-task PR |
|:-:|------|:----:|:--------:|:-----------:|
| 1 | L-D 잔존 3 skipped tests 사유 명시 (`docs/TESTING_NOTES.md`) | K-wave1 §5 #11 | Low | PR-1 |
| 2 | K-3 rate limit 3회/일/포스트 명시 코드 추가 | K-wave1 §5 #7 | Low | PR-2 |
| 3 | K-3 FeedItem/GalleryView 등 `<img>` alt sweep 완료 | K-wave1 §5 #8 | Low | PR-2 |
| 4 | K-5 작가 편집 페이지 도슨트 폼 추가 | K-wave1 §5 #9 | Medium | PR-3 |
| 5 | K-5 작가 편집 페이지 도슨트 opt-out 토글 UI 추가 | K-wave1 §5 #9 | Medium | PR-3 |
| 6 | FeedAlgo TypeScript 타입에 "v2" 추가 | K-wave1 §5 #6 | Low | PR-4 |
| 7 | i18n 키 자동 검증 CI 도입 (jq 또는 Node 스크립트) | K-wave1 §5 #10 | Low | PR-5 |
| 8 | K-2 diversity_reranker 관련 i18n 키 검증 통합 | CO-1 신규 | Low | PR-5 |
| 9 | K-8 ml_experiment_assignments 보존 기간 정책 명시 | CO-1 신규 | Low | PR-6 |
| 10 | K-3 caption_override 최대 길이 단위 테스트 추가 | CO-1 신규 | Low | PR-2 |
| 11 | K-5 DocentSection 별도 컴포넌트 분리 (inline → component) | K-wave1 §1.3 deviation | Low | PR-3 |

**Scope (sub-task PR 상세)**

- **PR-1: TESTING_NOTES.md 작성**
  - `docs/TESTING_NOTES.md` 신규 생성
  - L-D 잔존 3 skipped tests 사유 명시:
    - `test_dm_conversation_creation` — 현재 skip 사유 + 해제 조건
    - `test_dm_conversation_list` — 현재 skip 사유 + 해제 조건
    - (3번째: 실제 skip 대상 코드 확인 후 명시)
  - Phase 10 이후 테스트 정책 명시 (over-mocking 금지 원칙)

- **PR-2: K-3 rate limit + alt sweep + unit test**
  - `artwork_caption_jobs.py` — rate limit 명시 코드 추가 (3회/일/포스트 Redis counter)
  - FeedItem, GalleryView, SearchResultCard, NotificationCard 등 모든 `<img>` → `alt` 속성 sweep
  - `test_caption_rate_limit.py` — rate limit 3회 초과 시 429 응답 확인
  - `caption_override` 최대 길이(500자) 단위 테스트 추가

- **PR-3: K-5 도슨트 UI 완성 + DocentSection 분리**
  - 작가 편집 페이지 (`/posts/[id]/edit`) 도슨트 폼 추가:
    - `artist_docent_text` 직접 입력 textarea
    - "AI 도슨트 생성" 버튼 (POST `/posts/{id}/docent/generate` 호출)
    - opt-out 토글 UI (`PATCH /posts/{id}/docent/opt-out` 연결)
  - `DocentSection` inline 컴포넌트 → `src/components/DocentSection.tsx` 분리
  - 5 locale i18n 키: `docent.edit_page.*` 추가

- **PR-4: FeedAlgo TypeScript 타입 "v2" 추가**
  - `src/lib/api.ts` FeedAlgo 타입 확장: `"default" | "v1" | "v2" | "auto"`
  - K-8 Feature Flag 분기에서 "v2" algo 타입 사용 확인
  - tsc 0 errors 확인

- **PR-5: i18n 키 자동 검증 CI**
  - `.github/workflows/i18n-check.yml` 신규 또는 기존 CI에 통합
  - jq 스크립트: `ko.json` 기준 키 → `en/ja/zh/es.json` 누락 키 검출
  - 또는 Node 스크립트 `scripts/check-i18n.js` (package.json `lint:i18n` 명령)
  - K-2 신규 i18n 키 (`feed.discovery_badge`) 검증 포함
  - PR CI 단계에서 자동 실패 처리

- **PR-6: ml_experiments 보존 정책 + 운영 문서**
  - `docs/TESTING_NOTES.md`에 ml_experiments 90일 보존 정책 명시 (OQ-9 권장)
  - alembic scheduled cleanup 또는 cron 문서화 (Phase 11에서 구현)
  - K-8 experiment 종료 절차 문서 (`docs/runbook/ab-test-close.md`)

**Acceptance Criteria**

- [ ] `docs/TESTING_NOTES.md` 생성 + L-D 3 skipped tests 사유 명시 (PR-1)
- [ ] K-3 rate limit 3회/일 Redis counter 코드 확인 (PR-2)
- [ ] FeedItem/GalleryView/SearchResultCard 등 모든 `<img>` alt 속성 확인 (PR-2)
- [ ] 작가 편집 페이지 도슨트 폼 + opt-out 토글 UI 동작 확인 (PR-3)
- [ ] `DocentSection.tsx` 독립 컴포넌트로 분리 + import 확인 (PR-3)
- [ ] `FeedAlgo` 타입 "v2" 추가 + tsc 0 errors (PR-4)
- [ ] i18n CI 자동 검증 스크립트 동작 확인 (PR-5)
- [ ] ml_experiments 90일 보존 정책 문서화 (PR-6)

**Risks**

| 리스크 | 영향 | 대응 |
|--------|:----:|------|
| PR-3 편집 페이지 회귀 | 중간 | E2E 스모크 테스트로 작가 편집 플로우 검증 |
| i18n CI 오탐 (의도적 locale 차이) | 낮음 | 허용 목록(allowlist) 메커니즘 추가 |
| DocentSection 분리 후 동작 회귀 | 낮음 | 분리 전후 스냅샷 테스트 비교 |

**KPIs**

- 6 PR 모두 CI green 병합
- tsc errors: 0 (PR-4 후)
- 전체 테스트 회귀: 0건

---

## 5. Open Questions (OQ 목록)

사용자가 "권장대로" 한 번에 수락 가능하도록 권장 default를 명시한다.

| # | Open Question | 권장 Default | 근거 |
|:-:|---------------|:------------|------|
| **OQ-1** | K-8 PostHog Feature Flag 분배 비율 | **50:50 균등 분배** | 통계적 검정 가속, 표본 크기 동등 확보 |
| **OQ-2** | K-8 A/B 테스트 측정 기간 | **14일** | Phase 9 K Wave 1 권고(14일 운영)와 일치, 충분한 Bayesian 수렴 |
| **OQ-3** | K-2 diversity 가중치 초기값 | **신진작가 부스트 +20%, 장르 ≥ 3종, 지역 ≥ 2종, lambda=0.30** | 보수적 시작으로 개인화 품질 저하 최소화 |
| **OQ-4** | K-4 Featured Artist autopublish 정책 | **admin 검수 후 publish (autopublish OFF)** | ML 스코어 어뷰징 방지, 안전 우선 |
| **OQ-5** | K-7 컬렉션 자동 갱신 주기 | **주 1회 (월요일 09:00 UTC)** | K-4와 동일 요일 배치로 "주간 발견" 일관성 유지 |
| **OQ-6** | K-7 컬렉션 LLM 비용 한도 | **일 $5 한도** | translation_cache 히트율 ≥ 60% 가정 시 실제 $1~2/일 예상 |
| **OQ-7** | K-6 진입 거래 임계값 | **100건** | 이하 시 장르 배수 fallback만으로 정확도 불충분 |
| **OQ-8** | CO-1 carry-over PR 분리 정책 | **단일 sub-PDCA + 6 sub-task PR** | 독립 추적 가능 + 회귀 격리 |
| **OQ-9** | ml_experiments 테이블 보존 기간 | **90일 (분석 후 archive 또는 삭제)** | 통계 분석 충분 기간 + 스토리지 최적화 |
| **OQ-10** | A/B 테스트 통계 검정 도구 | **PostHog Insights 내장** | 별도 도구 도입 불필요, 이미 B'-5에서 활용 중 |
| **OQ-11** | Cold start 사용자 처리 (K-2 reranking 대상 여부) | **Chronological fallback 유지 (K-1 기존 구현, 변경 없음)** | 검증된 safe fallback, K-2 reranking 미적용으로 단순화 |
| **OQ-12** | K-2 다양성 가중치 튜닝 주기 | **월 1회 (diversity_constraints admin 편집)** | 운영 데이터 기반, 과도한 튜닝 방지 |
| **OQ-13** | K-4 cron 주기 | **주 1회 (월요일 06:00 UTC)** | K-7과 동일 요일, 06:00은 K-7(09:00) 3시간 선행 → Featured 결정 후 컬렉션 반영 가능 |
| **OQ-14** | CO-1 i18n CI 검증 도구 | **jq 스크립트 (GitHub Actions 내장, 의존성 Zero)** | Node 스크립트 대비 CI 환경 의존성 최소화 |
| **OQ-15** | K-6 거래 데이터 미달 시 처리 | **Phase 11 자동 이월 + Phase 10 report에 조건 미충족 명시** | 강제 진행 금지, 데이터 품질 보장 |

---

## 6. Wave 병렬 위임 전략

```
Week 0~2 (K-1 운영 관찰, 데이터 축적)
  ├── [사전 조건 확인] K-1 14일 운영 데이터 + interaction 500건+ 확인
  └── [분석] 장르/지역 분포 편중도 계산 → K-2 가중치 결정

Wave A (Week 2~4, 2 agents 병렬)
  ├── [Agent 1: bkend-expert] K-8 ML A/B 테스트 인프라 (alembic 0080)
  └── [Agent 2: bkend-expert] K-2 Diversity Reranking (alembic 0081)

Wave D (Week 2~3, 1 agent, Wave A와 병행)
  └── [Agent 3: bkend-expert + frontend-architect] CO-1 Carry-over 11항목 (PR-1~6 순차)

↓ (Wave A 완료 확인, ~Week 4)

Wave B (Week 4~6, 2 agents 병렬)
  ├── [Agent 1: bkend-expert + frontend-architect] K-4 Featured Artist (alembic 0082)
  └── [Agent 2: bkend-expert + frontend-architect] K-7 AI 큐레이션 컬렉션 (alembic 0083)

↓ (진입 조건 확인)

Wave C (Week 6~8, 조건부, 1 agent)
  └── [Agent 1: bkend-expert + frontend-architect] K-6 AI 가격 추천 (거래 ≥ 100건 시)
  └── [조건 미달 시] Phase 10 report에 명시 → Phase 11 이월
```

**병렬화 효율 예상**:
- Wave A 2 agents 병렬: K-8(7일) + K-2(7일) = 7일 (순차 14일 대비 50% 단축)
- Wave B 2 agents 병렬: K-4(7일) + K-7(7일) = 7일 (순차 14일 대비 50% 단축)
- Wave D Wave A 병행: CO-1(7~10일) 추가 오버헤드 없음

---

## 7. KPI 정의 (Phase 10 종결 시 측정)

### 7.1 Wave별 KPI 집계 기준

| sub-PDCA | 핵심 KPI | 목표값 | 측정 도구 |
|:--------:|---------|:------:|----------|
| **K-8** | Feed CTR v2 vs v1 delta | ≥ +15% | PostHog Experiment |
| **K-8** | A/B 통계적 유의성 | p < 0.05 | PostHog Insights |
| **K-8** | Session duration delta | ≥ +10% | PostHog |
| **K-2** | 장르 다양성 지수 | Shannon entropy ≥ 1.5 (≥ 3종) | 서버 메트릭 |
| **K-2** | 신진작가 피드 노출 비율 | ≥ 30% (팔로워 < 100) | Prometheus |
| **K-4** | Featured Artist CTR | ≥ 15% | PostHog |
| **K-4** | 신진작가 선정 비율 | ≥ 70% | DB 쿼리 |
| **K-7** | 컬렉션 CTR | ≥ 15% | PostHog |
| **K-7** | LLM 비용 | ≤ $35/주 | tuzigroup 사용량 |
| **K-6** | 가격 추천 사용률 | ≥ 50% | PostHog |
| **CO-1** | CI i18n 검증 PR green | 100% | GitHub Actions |

### 7.2 통합 KPI (Phase 10 종결)

| 지표 | 목표 | 비고 |
|------|:----:|------|
| 후원 전환율 (K-8 측정) | baseline 대비 ≥ 5% ↑ | K Wave 2 전체 효과 종합 |
| Retention D7 | baseline 대비 ≥ 10% ↑ | PostHog cohort analysis |
| Retention D30 | baseline 측정 시작 | Phase 11 목표 설정용 |
| ML 피드 cold user 비율 | ≤ 25% (K-2 신진작가 부스팅 효과) | Prometheus |
| 테스트 총 수 | 581 → 630+ | 신규 +49 이상 |
| alembic head | single head `0083_ai_collections` | 또는 K-6 진입 시 0084 |

---

## 8. Risks & Mitigation

| 리스크 | 영향 | 가능성 | 대응 |
|--------|:----:|:------:|------|
| **ML Cold Start (사용자 부족)** | 높음 | 중간 | K-2 Chronological fallback 유지(OQ-11). K-8 A/B 기간 14일 → 28일 연장 가능 |
| **A/B 테스트 통계 유의성 부족** | 높음 | 중간 | Bayesian A/B test (PostHog 내장). 14일 후 미달 시 28일 연장 결정 |
| **LLM 비용 폭증 (K-7)** | 높음 | 낮음 | 일 $5 hard cap + translation_cache 재사용 + cron 실패 시 fallback 없이 skip |
| **K-6 진입 조건 미달** | 중간 | 높음 | OQ-7 기준 100건 확인 후 Phase 11 이월. 강제 진입 금지 |
| **CO-1 UI 회귀** | 중간 | 낮음 | PR-3 E2E 스모크 테스트. PR-4 tsc 0 errors 확인. atomic PR 분리로 회귀 격리 |
| **K-4 ML 스코어 어뷰징** | 높음 | 낮음 | autopublish OFF 정책(OQ-4). admin 검수 필수. 최근 4주 선정 제외 규칙 |
| **K-7 클러스터링 품질 저하** | 중간 | 중간 | admin 큐 거부율 모니터링. k값 자동 튜닝 (k=5~8 범위 실험) |
| **Wave B K-4/K-7 alembic 충돌** | 중간 | 낮음 | alembic 0082/0083 사전 배정 (§9 마이그레이션 체인 준수) |

---

## 9. alembic Migration Chain

| revision | sub-PDCA | 테이블 | down_revision |
|----------|:--------:|--------|:-------------:|
| `0079_llm_docent` | K-5 (Phase 9) | posts +6 컬럼 | `0078_ai_artwork_caption` |
| **`0080_ml_experiments`** | **K-8** | `ml_experiments`, `ml_experiment_assignments` | `0079_llm_docent` |
| **`0081_diversity_constraints`** | **K-2** | `diversity_constraints` | `0080_ml_experiments` |
| **`0082_featured_artist_candidates`** | **K-4** | `featured_artist_candidates` | `0081_diversity_constraints` |
| **`0083_ai_collections`** | **K-7** | `ai_collections`, `ai_collection_posts` | `0082_featured_artist_candidates` |
| `0084_*` (예약) | K-6 (Wave C 진입 시) | TBD | `0083_ai_collections` |

> **충돌 방지 원칙**: Wave A(K-8/K-2)는 alembic 작업 없이 병렬 진행 후, 각 migration을 Wave A 완료 후 순차 merge. Wave B(K-4/K-7)도 동일 패턴.
>
> `alembic heads` 목표: Phase 10 종결 시 **single head `0083_ai_collections`** (K-6 미진입 시) 또는 **`0084_*`** (K-6 진입 시)

---

## 10. Phase 11 검토 후보

Phase 10 종결 후 운영 데이터 기반으로 우선순위 재평가.

| 후보 | 조건/근거 | 예상 우선순위 |
|------|----------|:------------:|
| **K-6 AI 가격 추천** | 거래 100건 미달 시 Phase 10 → 11 이월 | Must (이월) |
| **A/B 테스트 확장** | K-8 결과에 따른 ML 모델 추가 실험 (K-2 lambda 최적화 등) | Should |
| **모바일 Native (iOS/Android)** | README "주머니 앱" — 현재 web only. Phase 9 report 옵션 B | Should |
| **B2B Gallery Partnership** | "갤러리 입점 못하는 신진작가 직접 노출" 강화. Phase 9 report 옵션 C | Could |
| **Marketplace 분할 (Pro/Lite)** | 컬렉터 회비 모델 구체화. Phase 9 report 옵션 D | Should (Phase 11+) |
| **K-4 autopublish 전환** | K-4 운영 2개월 후 admin 승인율 ≥ 95% 달성 시 autopublish ON 고려 | Could |
| **실시간 WebSocket 피드 갱신** | L-C WebSocket 인프라 (Phase 9) 위에 피드 실시간 push | Could |
| **ML 모델 재학습 자동화** | K-8 A/B 결과 기반 자동 재학습 트리거 정교화 | Should |

---

## 11. Phase 10 타임라인 (예상)

| 기간 | 활동 | sub-PDCA | 상태 |
|:---:|------|:--------:|:----:|
| W1 | K-1 운영 데이터 관찰 + 장르/지역 편중 분석 + OQ 확정 | 사전 준비 | ⏳ |
| W2 | K-8 design + impl 시작 (alembic 0080) | K-8 | ⏳ |
| W2 | K-2 design + impl 시작 (alembic 0081) — K-8 병렬 | K-2 | ⏳ |
| W2 | CO-1 PR-1~PR-4 순차 병행 시작 | CO-1 | ⏳ |
| W3 | K-8 완료 + K-2 완료 + CO-1 PR-5~6 완료 | Wave A + D | ⏳ |
| W4 | K-4 design + impl 시작 (alembic 0082) | K-4 | ⏳ |
| W4 | K-7 design + impl 시작 (alembic 0083) — K-4 병렬 | K-7 | ⏳ |
| W5 | K-4 완료 + K-7 완료 | Wave B | ⏳ |
| W6 | 거래 100건+ 조건 확인 → K-6 진입 결정 | Wave C | ⏳ |
| W6~8 | K-6 (조건 충족 시) 또는 Phase 10 종결 | K-6 / 종결 | ⏳ |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-06 | Phase 10 초기 로드맵 작성. K Wave 2 (K-8/K-2/K-4/K-7/K-6) + CO-1 = 6 sub-PDCAs. OQ 15항목 권장 default 명시. alembic 0080~0083 사전 배정. | itpe-ince (Claude Sonnet 4.6) |
