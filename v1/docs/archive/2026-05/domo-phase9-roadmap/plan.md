---
template: plan
version: 1.0
feature: domo-phase9-roadmap
date: 2026-05-05
author: itpe-ince (Claude Sonnet 4.6)
project: domo
project_version: v1
parent_roadmap: Phase 9 (L: Carry-over Consolidation → K: ML Feed v2 + AI Curation)
status: Draft (Roadmap)
---

# Domo Phase 9 — 로드맵 (Master Plan)

> **Summary**: Phase 8 종결(15/15 sub-PDCA, 100%, 2026-05-05) 후 두 단계를 순차 진행한다. L: Carry-over Consolidation(3~4주, L-1~L-12, ~6-7 sub-PDCAs) — Phase 8 carry-over 13건 체계적 청산 (ML/번역 인프라 + 외부 콘텐츠 booster + DM 확장 + 테스트 부채 + a11y + 모니터링). K: ML Feed v2 + AI Curation(10주, K-1~K-8, ~6-8 sub-PDCAs) — README 비전 "AI 시대 작가 정체성 재정의" 직접 구현 (collaborative filtering 피드 + AI 캡션 + LLM 도슨트 + AI 큐레이션). 총 14 sub-PDCAs, 13~14주 계획.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-05-05
> **Status**: Roadmap (Sub-PDCA 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. Phase 9 배경 & 전략적 의미

### Phase 8 종결 성과

Phase 8은 G''(5/5) + H'(6/6) + B'(5/5) = 15/15(+G''-6 Phase 9 defer) sub-PDCA 완료(2026-05-05). 주요 성과:

- **Performance & Observability 완성**: OpenTelemetry X-Ray + Redis ElastiCache + N+1 audit + DB pool 튜닝 → HTTP p95 187ms, Redis cache hit 73%
- **Carry-over 청산**: Phase 7 16건 중 13건 청산 — VoiceOver/NVDA a11y + CJK PDF + Multi-language SEO + Click tracking + SES bounce
- **Patronage Maturity**: Multi-currency (USD/KRW/EUR/JPY) + DM 1:1 messaging + FCM/APNs Push + Stripe 자동 갱신 + 후원 분석 대시보드
- **누적 지표**: 311 → 412 tests (+101), alembic 0050~0065 (16 migrations), Cron 11개 R-5 격리, i18n 1500+ entries × 5 locales
- **Phase 8 defer**: G''-6 frontend-bundle-optimization + H'-5 open rate tracking + DM Group + WebSocket + file attachment DM + over-mocked test 7개 skipped

### Phase 9가 중요한 이유

Phase 5(후원 인프라) → Phase 6(그로스해킹) → Phase 7(마케팅 허브) → Phase 8(Patronage Maturity) 위에서 Phase 9는 두 가지 목표를 순차 달성한다:

**1. L — Carry-over Consolidation**: Phase 8 carry-over 13건을 L-1~L-12 체계적 청산. 특히 H'-6에서 준비한 50K+ behavioral events를 ML feed v2(K 단계)의 사전 인프라(L-1 임베딩 파이프라인)로 전환. 테스트 부채 정상화(7개 skipped), a11y WCAG AAA 대비, DM 확장(Group + WebSocket + 파일 첨부)도 이 단계에서 처리.

**2. K — ML Feed v2 + AI Curation**: README 비전의 가장 고도화된 구현 단계. "AI 시대 작가의 정체성"을 플랫폼 기능으로 직접 번역한다. Collaborative filtering 피드(K-1), AI 작품 캡션 자동 생성(K-3), LLM 도슨트(K-5), AI 가격 추천(K-6), AI 큐레이션 컬렉션(K-7)은 모두 README의 다음 문장을 구현한다:

> "AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음" — AI를 활용해 작가가 먹고살 수 있는 플랫폼 구조 구축.

> "전 세계 아티스트들의 인덱스를 만들고 싶음" — ML 기반 아티스트 발굴 + AI Featured Artist 추천으로 글로벌 신진작가 가시성 극대화.

> "히스토리를 두세 개 만든다" — LLM 도슨트와 AI 캡션으로 작품 스토리텔링 자동화. 언론/SNS 확산 가속.

```
[Phase 5] 후원 인프라 완성 (Stripe SetupIntent + Blue Bird 후원)
    ↓
[Phase 6] 그로스해킹 깔때기 + 신진작가 인덱스
    ↓
[Phase 7] 마케팅 허브 자동화 (AI 인터뷰 + Press Kit + Newsletter)
    ↓
[Phase 8] Performance & Observability + Patronage Maturity (Multi-currency + DM + Push)
    ↓
[Phase 9 L] Carry-over Consolidation — Phase 8 defer 13건 청산 + ML 사전 인프라
    ↓
[Phase 9 K] ML Feed v2 + AI Curation — 추천 고도화 + AI 작가 지원
```

---

## 1. 비즈니스 컨텍스트

### Phase 9 전략 포지셔닝

Phase 8까지는 "작가가 글로벌 후원을 받을 수 있는 인프라"가 목표였다. Phase 9는 그 위에서 **플랫폼이 능동적으로 작가를 발굴하고 후원자와 연결**하는 단계로 진화한다.

```
Phase 8까지의 Domo: 작가가 올린 콘텐츠를 사용자가 발견한다 (수동)
Phase 9 이후의 Domo: 플랫폼이 AI로 최적 콘텐츠를 추천하고 스토리를 생성한다 (능동)
```

### ML + AI가 README 비전을 완성하는 이유

| README 비전 | Phase 8 달성 | Phase 9 달성 |
|-------------|:----------:|:----------:|
| 글로벌 신진작가 후원 | Multi-currency 결제 실현 ✅ | AI Featured Artist 추천 → 발굴 확장 |
| 그로스해킹 깔때기 | DM + Push retention 강화 ✅ | ML 피드로 개인화 CTR ↑ → 더 많은 후원자 유입 |
| AI 시대 작가 생존 | Stripe 자동 갱신 96.3% ✅ | AI 캡션 + 도슨트로 작가 콘텐츠 가치 자동 증폭 |
| 글로벌 작가 인덱스 | Redis artist_index 캐시 ✅ | AI 큐레이션 + 협업 필터링으로 신진작가 발굴 자동화 |

### 데이터 준비 상태 (Phase 9 ML 진입 조건)

Phase 8 H'-6에서 축적된 행동 데이터:
- **50,847건** behavioral history records (view_post, like_post, save_post, visit_artist, sponsor_artist, click_story)
- **~1,200 events/day** 지속 수집
- L-1 임베딩 파이프라인 완성 시 → K-1 collaborative filtering 즉시 진입 가능

---

## 2. Phase 8 Carry-over 매핑 (L-1 ~ L-12)

Phase 8 report.md §9의 carry-over 13건을 Phase 9 L 단계 sub-PDCA로 매핑.

| # | Phase 8 Carry-over 항목 | Phase 8 근거 | Phase 9 L 매핑 | 우선순위 |
|---|------------------------|:----------:|:--------------:|:-------:|
| 1 | H'-6 ML feed v2 preparation (임베딩 인프라) | H'-6 데이터 준비 완료, 모델 학습 미진입 | **L-1** | Must |
| 2 | RSS auto-fetch cron (외부 매체 자동 수집) | H'-4 click tracking 완료, RSS fetch 시간 부족 | **L-2** | Should |
| 3 | Auto-thumbnail OG scraping 고도화 | H'-4 통합 구현, 정확도 91% → 95% 목표 | **L-3** | Could |
| 4 | Newsletter open rate 수집 (1x1 픽셀 + click tracking) | H'-5 bounce handling 완료, open rate 미구현 | **L-4** | Should |
| 5 | Group DM (3인 이상 대화방) | B'-2 1:1 완성, P3-1 Group Phase 9+ | **L-5** | Must |
| 6 | WebSocket 실시간 Push (DM/알림 실시간) | B'-2 polling 구현, WebSocket Phase 9+ | **L-6** | Must |
| 7 | File/Image attachment DM | B'-2 텍스트 only, 첨부파일 Phase 9+ | **L-7** | Should |
| 8 | Over-mocked test refactor (7개 skipped) | DMConversation/DeviceToken/NotificationPreferences class patch | **L-8** | Must |
| 9 | WCAG AAA 대비 (H'-1 후속) | H'-1 WCAG AA 달성, AAA 색상대비/포커스 관리 | **L-9** | Could |
| 10 | AAA cognitive a11y (난독증/인지장애 지원) | L-9 후속 — 단순 모드 토글 | **L-10** | Could |
| 11 | Translation memory (LLM Gateway 번역 캐싱) | Phase 7 C-3/G'-1 번역 자동화, 캐시 미구현 | **L-11** | Should |
| 12 | Cohort retention 자동 알림 (Phase 8 B'-5 후속) | B'-5 dashboard 완성, 임계치 알림 미구현 | **L-12** | Should |
| 13 | G''-6 frontend-bundle-optimization (완성) | Phase 8 198KB partial, 목표 미달 항목 잔존 | **L-1 통합** (ML 인프라 + 번들 최종화) | Must |

**L 단계 그룹화 전략** (6개 sub-PDCA로 통합):

| sub-PDCA | 포함 항목 | 핵심 목표 |
|:--------:|----------|----------|
| **L-A** | L-1 (임베딩 파이프라인) + G''-6 (번들 최적화) | ML 사전 인프라 + 번들 완성 |
| **L-B** | L-2 (RSS auto-fetch) + L-3 (OG 고도화) + L-4 (open rate) | 외부 콘텐츠 booster 3종 |
| **L-C** | L-5 (Group DM) + L-6 (WebSocket) + L-7 (파일 첨부) | DM 확장 3종 |
| **L-D** | L-8 (over-mocked test refactor) | 테스트 품질 부채 청산 |
| **L-E** | L-9 (WCAG AAA) + L-10 (cognitive a11y) | 접근성 AAA 대비 |
| **L-F** | L-11 (번역 메모리) + L-12 (cohort 자동 알림) | ML/번역 인프라 + 모니터링 |

---

## 3. README 비전 매핑

| README 원문 | Phase 9 sub-PDCA | 구현 방식 |
|------------|:----------------:|----------|
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | **K-3, K-5, K-6** | AI 작품 캡션 자동 생성(K-3) + LLM 도슨트 해설(K-5) + AI 가격 추천(K-6) — 작가가 AI 도구를 직접 활용해 작품 가치를 증폭 |
| **"전 세계 아티스트들의 인덱스를 만들고 싶음"** | **K-1, K-4, K-7** | Collaborative filtering 피드(K-1)로 신진작가 발굴 + AI Featured Artist 추천(K-4) + AI 큐레이션 컬렉션(K-7) — 알고리즘이 자동으로 글로벌 신진작가를 인덱싱 |
| **"유저들이 늘어나야 소비자들도 늘어남" — 그로스해킹** | **K-1, K-2, K-8** | ML 피드 v2(K-1)로 개인화 CTR ↑ → 더 많은 후원자 유입. Diversity reranking(K-2)으로 필터 버블 방지 → 신규 발굴 기회. A/B 테스트(K-8)로 피드 효과 측정 |
| **"히스토리를 두세 개 만든다" — 스토리텔링** | **K-3, K-5** | AI 캡션(K-3)으로 alt text + SEO 자동화. LLM 도슨트(K-5)로 작품 배경 + 작가 의도 hybrid 설명 — 언론/SNS 확산 콘텐츠 자동 생성 |
| **"후원 개념을 넣고 후원할 수 있는 구조를 만듦"** | **K-6, K-8** | AI 가격 추천(K-6)으로 신진작가 reserve_price 최적화 → 경매 낙찰률 ↑. A/B 테스트(K-8)로 ML 피드 후원 전환율 측정 |
| **"동유럽이든 남미든 동아시아든 이런 데들에게는 꿈과 희망"** | **L-11, K-4** | 번역 메모리(L-11)로 LLM 번역 비용 ↓ + 품질 ↑. AI Featured Artist(K-4)로 지역 불문 신진작가 자동 추천 |
| **"컬렉터들한테는 회비 1년에 10분씩"** | **K-7, K-8** | AI 큐레이션 컬렉션(K-7)으로 컬렉터 관심 주제별 작품 묶음 → 회비 가치 증가. A/B 테스트(K-8)로 컬렉터 retention 측정 |

---

## 4. Sub-PDCA 상세

### L 단계 — Carry-over Consolidation (3~4주)

---

#### L-A: ML 임베딩 인프라 + 번들 최적화 완성

**Feature ID**: `ml-embedding-infra-bundle-final`
**우선순위**: Must
**예상 기간**: ~5일
**의존성**: 없음 (Critical Path — K-1 collaborative filtering 사전 조건)
**Booster 관계**: H'-6 (50K+ events DB 준비 완료) + G''-5 (198KB partial 완성)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

H'-6에서 구축한 behavioral history table을 ML feed v2(K-1)에서 바로 활용할 수 있도록 특징 벡터/임베딩 파이프라인을 구성한다. 동시에 Phase 8에서 partial 처리된 G''-6 frontend bundle을 최종 목표 수준으로 완성한다.

**Scope**

- 백엔드 임베딩 파이프라인:
  - user_embedding table (user_id, embedding_vector JSON, computed_at)
  - item_embedding table (post_id, embedding_vector JSON, tags, genre, computed_at)
  - alembic 0066: user_embedding + item_embedding 테이블
  - Embedding cron (embedding_compute_jobs.py, R-5 격리, 일 1회)
  - tuzigroup LLM Gateway 또는 sentence-transformers 로컬 모델 선택 (OQ-1 결정)
- 프론트엔드 번들 최종화:
  - next/bundle-analyzer 기반 잔존 큰 chunk 추가 분리
  - Konva.js (A-image-studio) tree-shaking 최적화
  - Initial bundle ≤ 180KB (Phase 8 목표 200KB → 강화)
  - Lighthouse performance ≥ 90 (Phase 8 86 → 강화)

**Acceptance Criteria**

- [ ] user_embedding + item_embedding 테이블 생성 (alembic 0066 green)
- [ ] 임베딩 cron 정상 동작 (50K+ behavioral history → 임베딩 계산)
- [ ] Initial bundle ≤ 180KB (next/bundle-analyzer 확인)
- [ ] Lighthouse performance ≥ 90 (CI 자동 측정)
- [ ] K-1 collaborative filtering에서 임베딩 테이블 직접 참조 가능 확인

**Risks**

- 임베딩 모델 선택 (OQ-1): 로컬 sentence-transformers vs tuzigroup API — 추론 속도 vs 품질 트레이드오프
- Konva.js 번들 분리 시 동작 회귀 위험 → dynamic import 적용 후 E2E 검증 필수

**KPIs**

- Embedding compute latency: ≤ 5min (50K events 기준 일괄 계산)
- Bundle size: ≤ 180KB
- Lighthouse perf: ≥ 90

---

#### L-B: 외부 콘텐츠 Booster 3종 (RSS + OG 고도화 + Open Rate)

**Feature ID**: `external-content-booster`
**우선순위**: Should
**예상 기간**: ~5일
**의존성**: 없음 (독립)
**Booster 관계**: H'-4 (click tracking + thumbnail), H'-5 (SES bounce), C-4 (media coverage)
**담당 agent**: bkend-expert

**Goal**

Phase 8 H'-4에서 시간 부족으로 defer된 RSS auto-fetch와 open rate tracking을 완성한다. 외부 매체 기사를 자동으로 수집하고, newsletter open rate를 1x1 픽셀 방식으로 추적한다.

**Scope**

- L-2 RSS auto-fetch:
  - rss_feed_jobs.py (R-5 격리, 4시간마다 실행)
  - 등록된 media source RSS endpoint 자동 수집
  - 신규 기사 자동 C-4 media coverage 등록 + admin 승인 큐
  - alembic 0067: rss_source table (url, last_fetched, is_active)
- L-3 Auto-thumbnail OG 고도화:
  - H'-4 기존 91% → 95%+ 정확도 목표
  - og:image 추출 실패 시 대체 이미지 우선순위 체계 (og → twitter:image → first_img → default)
  - thumbnail cache 7일 TTL (Redis G''-2 booster)
- L-4 Newsletter open rate 1x1 픽셀:
  - GET /api/newsletter/track/{token}.gif (1x1 투명 픽셀 반환)
  - token: base64(user_id + newsletter_id + timestamp) HMAC 서명
  - open event DB 저장 → B'-5 analytics dashboard booster
  - click tracking: newsletter 내 링크 → /api/newsletter/click/{token}?url= redirect

**Acceptance Criteria**

- [ ] RSS auto-fetch cron 정상 동작 (4h interval, 5개 이상 source 등록)
- [ ] Thumbnail 추출 성공률 ≥ 95%
- [ ] 1x1 픽셀 open tracking 정상 동작 (GET 요청 → DB 저장 확인)
- [ ] Click tracking redirect 정상 동작 (PostHog event 발화 확인)
- [ ] B'-5 analytics dashboard에 newsletter open rate 표시

**Risks**

- RSS source가 HTML만 제공 시 파싱 실패 → BeautifulSoup fallback 처리
- Gmail/Apple Mail image blocking → 1x1 픽셀 open rate 과소 측정 필연적 (알려진 한계, 안내 문구 추가)

**KPIs**

- RSS 수집 성공률: ≥ 95% (등록 source 기준)
- Newsletter open rate 측정 정확도: ≥ 70% (Gmail 제약 감안)

---

#### L-C: DM 확장 3종 (Group DM + WebSocket + 파일 첨부)

**Feature ID**: `dm-expansion`
**우선순위**: Must
**예상 기간**: ~7일
**의존성**: B'-2 DM messaging 완료 (Phase 8 ✅)
**Booster 관계**: B'-2 (Conversation/Message 모델), B'-3 (Push notification)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 8 B'-2에서 1:1 DM만 구현했던 것을 확장해 Group DM(P3-1 Community 첫 구현), WebSocket 실시간 push, 파일/이미지 첨부를 완성한다.

**Scope**

- L-5 Group DM:
  - GroupConversation 모델 + alembic 0068 (group_conversations, group_participants)
  - 3인 이상 그룹 생성 (최대 50인 제한)
  - 그룹 관리자(creator) 역할 — 참여자 추가/제거, 그룹명 수정
  - API: POST /api/group-conversations, POST /api/group-conversations/{id}/participants
  - 그룹 DM 수신 시 B'-3 Push dispatch booster
- L-6 WebSocket 실시간:
  - FastAPI WebSocket endpoint (/ws/conversations/{id})
  - Connection manager (user_id → ws connection 맵핑)
  - 메시지 수신 즉시 broadcast (polling 1s → 실시간 전환)
  - Reconnect 로직 (heartbeat 30s + exponential backoff)
  - Redis pub/sub (G''-2 booster) — 다중 서버 인스턴스 대응
- L-7 파일/이미지 첨부:
  - MessageAttachment 모델 + alembic 0069 (message_attachments)
  - 허용 타입: image/jpeg, image/png, image/gif, image/webp, application/pdf (≤ 10MB)
  - AWS S3 업로드 (Phase 7 C-2 S3 booster)
  - 첨부 이미지 미리보기 (thumbnail 생성 backend)
  - 모더레이션: 이미지 업로드 시 Phase 8 admin abuse queue 연동

**Acceptance Criteria**

- [ ] Group DM 생성 및 3인 이상 대화 정상 동작
- [ ] WebSocket 실시간 메시지 수신 (polling 제거 또는 fallback 유지)
- [ ] 파일 첨부 업로드 + 다운로드 정상 동작
- [ ] alembic 0068, 0069 green (upgrade + downgrade 테스트)
- [ ] Group DM 수신 시 Push notification 발화 확인

**Risks**

- WebSocket 다중 인스턴스 시 broadcast 누락 → Redis pub/sub 필수 (L-6 scope에 포함)
- 이미지 첨부 모더레이션 속도 → 비동기 처리 (즉시 표시 후 백그라운드 검토)
- Group DM 스팸 → rate limit 5 messages/min/user/group + report 기능 필수

**KPIs**

- WebSocket 메시지 전달 지연: ≤ 100ms (p95)
- 파일 업로드 성공률: ≥ 99%
- Group DM 최대 참여자 50인 대응 확인

---

#### L-D: Over-mocked Test Refactor

**Feature ID**: `test-quality-refactor`
**우선순위**: Must
**예상 기간**: ~3일
**의존성**: L-C (DM 확장) 완료 후 진행 권장 (DM 모델 안정화 후 테스트 정상화)
**Booster 관계**: Phase 8 B'-2, B'-3 — skip된 테스트 7개 모두 해당 모델 관련
**담당 agent**: bkend-expert

**Goal**

Phase 8에서 `class patch` 방식 over-mocking으로 skip된 테스트 7개를 실제 DB 또는 서비스 레이어를 사용하는 통합 테스트로 정상화한다.

**Scope**

- 대상 테스트 (7개 skipped):
  1. `test_dm_conversation_creation` — DMConversation class patch
  2. `test_dm_conversation_list` — DMConversation class patch
  3. `test_device_token_register` — DeviceToken class patch
  4. `test_device_token_refresh` — DeviceToken class patch
  5. `test_notification_preferences_update` — NotificationPreferences class patch
  6. `test_notification_send_push` — NotificationPreferences + DeviceToken patch
  7. `test_notification_email_digest` — NotificationPreferences class patch
- 각 테스트를 `pytest + SQLAlchemy test DB` 통합 테스트로 재작성
- Mock 허용 범위: 외부 서비스(FCM, APNs, SES)만 Mock — 내부 DB 로직은 실제 실행
- 테스트 DB: `sqlite:///:memory:` 또는 `PostgreSQL test DB` (OQ-2 결정)

**Acceptance Criteria**

- [ ] 7개 skipped 테스트 모두 pass 전환
- [ ] 기존 412 tests 회귀 없음 (419+ tests passed)
- [ ] `pytest -v` 결과에서 "SKIPPED" 0건 (허용된 skip 제외)
- [ ] Coverage ≥ 90% (DMConversation/DeviceToken/NotificationPreferences 관련 모듈)

**Risks**

- 실제 DB 테스트 전환 시 격리 실패 (test 간 state 오염) → `@pytest.fixture(scope="function")` + rollback 패턴 필수
- CI 속도 증가 → 병렬 pytest-xdist 적용 고려

**KPIs**

- Test pass count: 412 → 419+ passed (7개 복구)
- Test skipped count: 7 → 0

---

#### L-E: WCAG AAA 접근성 강화

**Feature ID**: `wcag-aaa-accessibility`
**우선순위**: Could
**예상 기간**: ~4일
**의존성**: 없음 (독립, H'-1 WCAG AA 기반)
**Booster 관계**: H'-1 (VoiceOver/NVDA audit_report v0.4)
**담당 agent**: frontend-architect

**Goal**

Phase 8 H'-1에서 WCAG 2.1 Level AA를 달성했다. Level AAA의 핵심 조건인 색상 대비(7:1 이상), 포커스 관리 고도화, 그리고 인지 장애 사용자를 위한 단순 모드 토글을 추가한다.

**Scope**

- L-9 WCAG AAA 색상 대비 + 포커스:
  - 핵심 페이지(피드/포스트/경매) 색상 대비 7:1 달성 (AAA)
  - Focus ring 강화 (2px solid + offset 2px + color-contrast 자동 감지)
  - 키보드 내비게이션 완전 지원 (모달/드롭다운/슬라이더)
  - `prefers-reduced-motion` CSS 미디어 쿼리 통합 (애니메이션 비활성화)
- L-10 Cognitive Accessibility 단순 모드:
  - "단순 모드" 토글 (UserPreference 필드 추가 + alembic 0070)
  - 단순 모드 활성화 시:
    - 피드 카드에서 광고/프로모션 숨김
    - 폰트 크기 1.2× 자동 적용
    - 줄 간격 1.5× 자동 적용
    - 배경 패턴 제거 (plain white/dark)
  - 5 locale 단순 모드 UI 텍스트 i18n

**Acceptance Criteria**

- [ ] 핵심 3개 페이지(피드/포스트/경매) 색상 대비 7:1 달성 (DevTools 검증)
- [ ] 키보드 Tab 내비게이션 모든 인터랙티브 요소 접근 가능
- [ ] `prefers-reduced-motion` 애니메이션 비활성화 동작 확인
- [ ] 단순 모드 토글 — 5개 변경 사항 모두 즉시 반영
- [ ] alembic 0070 (user.simple_mode) green

**Risks**

- 색상 대비 7:1 달성 시 기존 브랜드 컬러 변경 필요 가능성 → 핵심 텍스트만 AAA, 장식 요소는 AA 유지 허용 (OQ-3 결정)
- 단순 모드 구현 복잡도 → CSS custom property 기반 전역 변수 교체 방식 권장

**KPIs**

- WCAG AAA 달성 페이지: 피드, 포스트 상세, 경매 (3페이지)
- axe-core AAA 위반: 0 (핵심 3페이지)

---

#### L-F: 번역 메모리 + Cohort 자동 알림

**Feature ID**: `translation-memory-cohort-alert`
**우선순위**: Should
**예상 기간**: ~4일
**의존성**: 없음 (독립)
**Booster 관계**: Phase 7 C-3 (multi-language story), G'-1 (LLM Gateway), Phase 8 B'-5 (cohort dashboard)
**담당 agent**: bkend-expert

**Goal**

tuzigroup LLM Gateway를 통한 번역 결과를 DB + Redis에 캐싱해 비용을 절감하고, Phase 8 B'-5 cohort retention dashboard에서 임계치 미달 시 Slack 알림을 자동 발송한다.

**Scope**

- L-11 Translation Memory:
  - translation_cache table (source_text_hash, target_locale, translated_text, model, created_at)
  - alembic 0071: translation_cache
  - 번역 요청 전 hash → DB lookup (cache hit → LLM Gateway 호출 생략)
  - Redis TTL 24h (G''-2 booster) + DB 영구 저장 (30일 이상 재사용)
  - 적용 범위: C-3 story 번역, Press Kit 번역, newsletter 번역 캡션
  - 예상 비용 절감: 번역 요청 60%+ 캐시 hit 목표
- L-12 Cohort 자동 알림:
  - B'-5 dashboard cohort retention 기준 (D7 < 50%, D30 < 30%) 임계치 미달 시
  - Slack Incoming Webhook → #analytics-alerts 채널 자동 발송
  - 알림 내용: 해당 cohort 날짜, retention 수치, dashboard 링크
  - alert_history table (alembic 0072) — 중복 알림 방지 (24h cooldown)
  - Cron: cohort_alert_jobs.py (R-5 격리, 매일 09:00 UTC)

**Acceptance Criteria**

- [ ] 동일 원문 번역 요청 시 DB cache hit → LLM Gateway 미호출 확인
- [ ] Redis TTL 24h 캐시 동작 확인
- [ ] D7 retention < 50% 시 Slack 알림 발송 확인 (테스트 시뮬레이션)
- [ ] 24h 중복 알림 방지 동작 확인
- [ ] alembic 0071, 0072 green

**Risks**

- 번역 캐시 만료 정책: LLM 모델 변경 시 이전 번역 품질 저하 → model 필드로 버전 관리 (모델 변경 시 cache invalidation)
- Slack Webhook URL 노출 → `.env` 변수 관리 필수

**KPIs**

- 번역 캐시 hit rate: ≥ 60% (14일 운영 후)
- LLM Gateway 번역 비용 절감: ≥ 50% (캐시 미적용 대비)
- Cohort 알림 발송 정확도: 100% (임계치 미달 시 누락 0)

---

### K 단계 — ML Feed v2 + AI Curation (10주)

README 비전 "AI 시대 작가" / "그로스해킹 funnel" 고도화. L-A 임베딩 파이프라인을 기반으로 8개 K sub-PDCA를 구현한다.

---

#### K-1: Collaborative Filtering 피드 v2

**Feature ID**: `ml-feed-collaborative-filtering`
**우선순위**: Must
**예상 기간**: ~14일
**의존성**: L-A (임베딩 파이프라인 완성) 필수
**Booster 관계**: L-A (user/item embedding), H'-6 (50K+ behavioral history), G''-2 (Redis feed cache)
**담당 agent**: bkend-expert

**Goal**

H'-6 behavioral history + L-A 임베딩을 기반으로 Matrix Factorization 또는 Two-Tower 모델을 학습하고, 기존 룰 기반 피드 스코어링을 ML 개인화 피드로 교체한다.

**Scope**

- 모델 선택 (OQ-4 결정):
  - Matrix Factorization (implicit 라이브러리, 빠른 구현, 행동 데이터만 사용)
  - Two-Tower 모델 (사용자 + 아이템 임베딩 분리, 더 높은 정확도)
- 모델 학습 파이프라인:
  - model_training_jobs.py (R-5 격리, 주 1회 재학습)
  - 학습 데이터: user_behavior_history (50K+ events) + user_embedding + item_embedding
  - 모델 직렬화: pickled model → S3 저장 (버전 관리)
- 추론 서비스:
  - app/services/ml_feed_service.py (async, Redis cache)
  - GET /api/feed → ML 스코어 기반 정렬 (기존 feed_scoring_jobs 대체)
  - Cold start 처리: 행동 이력 < 10개 사용자 → 인기 기반 fallback
  - 캐시: user별 feed_score 5min TTL (G''-2 Redis booster)
- 모델 성능 지표:
  - Precision@K (K=10): 추천 상위 10개 중 실제 클릭 비율
  - Recall@K: 사용자가 클릭한 것 중 추천에 포함된 비율
  - NDCG@K: 순위 고려 품질 지표

**Acceptance Criteria**

- [ ] 모델 학습 완료 (50K+ events → Precision@10 ≥ 0.15)
- [ ] GET /api/feed → ML 스코어 정렬 동작 확인
- [ ] Cold start fallback 동작 확인 (행동 이력 0건 사용자)
- [ ] Redis feed cache hit rate ≥ 70%
- [ ] K-8 A/B 테스트 피드 v1 vs v2 비교 준비 완료

**Risks**

- 50K events가 충분하지 않을 경우 → Precision@10 < 0.10 → 모델 단순화 (인기도 가중치 blend)
- 추론 latency 급증 → Redis 캐시 + 비동기 사전 계산으로 완화
- 모델 편향 (popular artist 쏠림) → K-2 diversity reranking으로 보완

**KPIs**

- Feed CTR: Phase 8 baseline 대비 ≥ 15% 향상 (K-8 A/B 측정)
- Precision@10: ≥ 0.15
- Feed API 응답시간 p95: ≤ 200ms (캐시 포함)

---

#### K-2: Diversity Reranking (필터 버블 방지)

**Feature ID**: `feed-diversity-reranking`
**우선순위**: Must
**예상 기간**: ~5일
**의존성**: K-1 (ML 피드 v2 완성) 필수
**Booster 관계**: K-1 (ML 스코어), G'-5 (artist_index genre/region tag)
**담당 agent**: bkend-expert

**Goal**

ML 피드(K-1)가 특정 장르/지역 작가에 편중되는 필터 버블 현상을 방지하기 위해, 추천 결과에 장르 다양성과 지역 다양성 제약을 적용한다.

**Scope**

- Maximal Marginal Relevance(MMR) 알고리즘 또는 규칙 기반 reranking:
  - 상위 50개 ML 스코어 후보 → 다양성 제약 적용 → 최종 20개 반환
  - 장르 제약: 상위 20개 중 동일 장르 ≤ 5개 (25%)
  - 지역 제약: 상위 20개 중 동일 국가/지역 ≤ 7개 (35%)
  - 다양성 가중치 λ (OQ-5 결정, 권장 0.3)
- 신진작가 부스팅:
  - 팔로워 < 100 또는 포스트 수 < 10인 신진작가에게 +10% 스코어 가산
  - "Domo Discovery" 배지 UI 추가 (신진작가 발굴 강조)
- app/services/ml_feed_service.py에 reranking layer 추가

**Acceptance Criteria**

- [ ] 동일 장르 5개 초과 시 후순위로 밀림 동작 확인
- [ ] 신진작가 부스팅 → 팔로워 < 100 작가 피드 노출율 ≥ 30% 증가
- [ ] "Domo Discovery" 배지 5 locale UI 확인
- [ ] Reranking 후 ML 추천 품질(NDCG@K) 저하 ≤ 5% 허용

**Risks**

- 다양성 가중치 λ 과다 시 개인화 품질 저하 → K-8 A/B 테스트로 최적값 탐색
- 장르 태그 누락 포스트 처리 → genre=null 포스트는 별도 "미분류" 버킷으로 처리

**KPIs**

- 장르 다양성 지수: 상위 20 피드 중 ≥ 4개 장르 (Shannon entropy ≥ 1.8)
- 신진작가 발굴율: 주간 피드에서 팔로워 < 100 작가 노출 ≥ 30%

---

#### K-3: AI 작품 자동 캡션 생성

**Feature ID**: `ai-artwork-caption`
**우선순위**: Must
**예상 기간**: ~7일
**의존성**: 없음 (독립, L-A 완성 후 권장)
**Booster 관계**: tuzigroup LLM Gateway (Phase 7 인프라), L-11 (번역 메모리), H'-1 (alt text a11y)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작가가 작품 이미지를 업로드하면, tuzigroup LLM Gateway(vision 모델)를 통해 작품 설명 캡션을 자동 생성한다. 생성된 캡션은 alt text(접근성), SEO meta description, 작품 상세 페이지 보조 설명으로 활용된다.

**Scope**

- 백엔드:
  - POST /api/posts/{id}/generate-caption (작가 전용)
  - tuzigroup LLM Gateway vision 모델 호출 (이미지 URL + 프롬프트)
  - 프롬프트: "이 작품의 장르, 기법, 감정, 주제를 한국어로 2~3문장 설명하라"
  - caption_generated_at, caption_text 필드 (alembic 0073: posts 테이블 확장)
  - L-11 번역 메모리 booster: 생성된 캡션 → 5 locale 자동 번역 (캐시 우선)
- 프론트엔드:
  - 포스트 편집 화면: "AI 캡션 생성" 버튼 + 편집 가능한 textarea
  - 생성 중 loading spinner + "AI가 작품을 분석하는 중..."
  - alt text 자동 설정 (H'-1 a11y booster)
  - SEO: og:description + meta description 자동 설정 (H'-3 booster)
- 모더레이션:
  - 부적절 내용 필터 (tuzigroup Gateway safety filter 활용)
  - 생성 실패 시 "캡션 생성에 실패했습니다. 직접 입력해주세요." 안내

**Acceptance Criteria**

- [ ] AI 캡션 생성 버튼 → LLM Gateway 호출 → 결과 표시 (3~5초 내)
- [ ] 생성된 캡션 → alt text 자동 설정 (axe-core 통과)
- [ ] 5 locale 자동 번역 적용 (L-11 번역 메모리 캐시 활용)
- [ ] 생성 실패 시 graceful fallback (에러 메시지 + 수동 입력 안내)
- [ ] alembic 0073 green

**Risks**

- LLM Gateway 추론 지연 (3~5초) → 비동기 처리 (생성 중 버튼 disabled + loading)
- 추상화 작품(비구상화)에서 설명 품질 저하 → 프롬프트 개선 또는 "AI 캡션 품질이 낮을 수 있습니다" 안내
- 비용 급증 → L-11 번역 메모리 캐시 + 요청 횟수 제한 (1포스트당 최대 3회/일)

**KPIs**

- 캡션 생성 성공률: ≥ 95%
- 작가 캡션 수정률: ≤ 40% (AI 생성 캡션 그대로 사용 ≥ 60%)
- 캡션 적용 포스트 SEO score 개선: Lighthouse SEO ≥ 99 (캡션 없는 포스트 대비)

---

#### K-4: AI Featured Artist 추천

**Feature ID**: `ai-featured-artist`
**우선순위**: Must
**예상 기간**: ~7일
**의존성**: K-1 (ML 피드 완성) 권장, L-A (임베딩) 필수
**Booster 관계**: Phase 7 G'-7 (admin manual featured), K-1 (ML 스코어), B'-5 (cohort retention)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

Phase 7 G'-7에서 admin이 수동으로 Featured Artist를 선정하던 것을 ML 알고리즘 자동 추천으로 전환한다. 매주 자동으로 "주간 추천 신진작가"를 선정해 홈/피드 상단에 노출한다.

**Scope**

- Featured Artist 스코어링:
  - 다음 가중합으로 주간 score 계산:
    - 최근 7일 팔로워 증가율 (40%)
    - 포스트 engagement rate (like + comment + save / view) (30%)
    - 신진작가 여부 (팔로워 < 1000, 가입 < 12개월) 부스팅 (20%)
    - 다양성 보정 (장르/지역 언더-represented) (10%)
  - 상위 3명 자동 선정 → admin 확인 큐 (승인/거부 가능)
  - featured_artist_weekly table (alembic 0074)
- 노출:
  - 홈 상단 "이번 주 추천 신진작가" 섹션 (3명 카드)
  - 피드 중간 삽입 (10번째 포스트마다 Featured Artist 배너)
  - 5 locale i18n ("이번 주 추천 신진작가", "This Week's Rising Artists" 등)
- admin 큐:
  - GET /api/admin/featured-artists/candidates (ML 추천 3명 + 스코어 이유)
  - POST /api/admin/featured-artists/{id}/approve
  - POST /api/admin/featured-artists/{id}/reject

**Acceptance Criteria**

- [ ] 주간 featured artist 자동 스코어링 cron 동작 (weekly_featured_jobs.py, R-5 격리)
- [ ] admin 큐에서 승인/거부 동작 확인
- [ ] 홈 상단 + 피드 배너 노출 (5 locale)
- [ ] 신진작가(팔로워 < 1000) 선정 비율 ≥ 70%
- [ ] alembic 0074 green

**Risks**

- ML 스코어 조작 가능성 (특정 작가 어뷰징) → admin 최종 승인 필수 유지
- 동일 작가 반복 선정 → 최근 4주 내 선정 작가 제외 규칙

**KPIs**

- Featured Artist 클릭률(CTR): ≥ 15% (홈 상단 카드 기준)
- 신진작가 선정 비율: ≥ 70%
- 후원 전환율 (Featured → 후원): baseline 측정 시작

---

#### K-5: LLM 도슨트 — 작품 해설

**Feature ID**: `llm-docent-artwork`
**우선순위**: Should
**예상 기간**: ~7일
**의존성**: K-3 (AI 캡션 기반) 권장, tuzigroup LLM Gateway
**Booster 관계**: K-3 (AI 캡션), L-11 (번역 메모리), Phase 7 C-1 (AI 인터뷰 자동 생성)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작품 상세 페이지에 LLM 기반 도슨트(해설사) 기능을 추가한다. 작가가 직접 입력한 설명 + AI가 생성한 예술사적/기법적 해설을 hybrid로 제공해 컬렉터와 일반 관람자의 작품 이해를 돕는다.

**Scope**

- AI 해설 생성:
  - POST /api/posts/{id}/generate-docent (작가 전용)
  - 프롬프트: 작품 이미지 + 작가 설명 + 장르 태그 → "이 작품의 예술사적 맥락, 사용된 기법, 감상 포인트를 전문 도슨트 스타일로 3~5문장 설명하라"
  - docent_text 필드 (alembic 0075: posts 테이블 확장)
  - L-11 번역 메모리: 5 locale 자동 번역 (캐시 우선)
- 작품 상세 UI:
  - "작가의 말" (작가 직접 입력) vs "AI 도슨트" (LLM 생성) — 탭 전환
  - AI 도슨트 섹션에 "이 해설은 AI가 생성했습니다" 명시 (투명성)
  - 음성 읽기(TTS) 버튼 — 브라우저 Web Speech API (선택, OQ-6 결정)
- 도슨트 퀴즈 (optional):
  - AI 생성 퀴즈 1~2개 (작품 감상 참여 유도) — 컬렉터 retention 강화
  - 정답 시 포스트 like 자동 처리 (engagement booster)

**Acceptance Criteria**

- [ ] AI 도슨트 생성 → 작품 상세 페이지 표시 (5초 내)
- [ ] "작가의 말" vs "AI 도슨트" 탭 전환 정상 동작
- [ ] "AI 생성" 투명성 문구 5 locale 표시
- [ ] 5 locale 번역 자동 적용 (L-11 캐시 활용)
- [ ] alembic 0075 green

**Risks**

- AI 해설 오류 (잘못된 예술사 정보) → "AI 생성" 명시 + 작가 수정 가능 → 책임 문제 완화
- 비용 급증 → 도슨트 생성 1포스트당 최대 2회/일 제한 + L-11 번역 캐시 필수

**KPIs**

- 도슨트 적용 포스트 체류 시간: 미적용 대비 ≥ 40% 증가 (PostHog 측정)
- 작가 도슨트 수정률: ≤ 30% (AI 품질 기준)

---

#### K-6: AI 가격 추천 (경매 reserve_price)

**Feature ID**: `ai-price-recommendation`
**우선순위**: Should
**예상 기간**: ~5일
**의존성**: K-1 (ML 피드) 권장, 경매 DB 데이터 필요
**Booster 관계**: Phase 5 B-1 (경매 기본 구조), Phase 6 A-6 (auction endpoint), K-1 (ML 스코어)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

작가가 경매를 등록할 때 reserve_price(최저 낙찰가)를 설정하기 어려운 문제를 해결하기 위해, AI 기반 가격 추천 기능을 제공한다. 유사 작품의 과거 낙찰가 + 작가 인기도 + 장르 시장 데이터를 기반으로 추천한다.

**Scope**

- 가격 추천 알고리즘:
  - 유사 작품 탐색 (임베딩 유사도 top-5 비교 작품)
  - 과거 낙찰가 중앙값 + 작가 ML 스코어 가중치
  - 장르별 시장 배수 (예: 유화 1.8×, 수채화 1.2×, 디지털 아트 0.9×)
  - 추천 범위: min~max (예: "₩150,000 ~ ₩250,000 권장")
- POST /api/auctions/price-recommend (작품 ID + 장르 + 재료 입력)
- 경매 등록 UI:
  - reserve_price 입력 필드 옆 "AI 가격 추천" 버튼
  - 추천 범위 + 근거 ("유사 작품 5개 평균 낙찰가 기준") 표시
  - "추천가 적용" 버튼으로 자동 입력
- 면책 문구: "이 추천은 참고용이며 실제 낙찰가를 보장하지 않습니다"

**Acceptance Criteria**

- [ ] 작품 ID 입력 → 가격 추천 범위 반환 (1~2초 내)
- [ ] 유사 작품 5개 이상 임베딩 유사도 기반 탐색 동작
- [ ] 경매 등록 UI에서 추천 적용 버튼 동작
- [ ] 면책 문구 5 locale 표시
- [ ] 추천 가격 범위 PostHog 이벤트 로깅 (K-8 A/B 분석용)

**Risks**

- 과거 낙찰 데이터 부족 (초기) → 장르 배수만 사용하는 fallback 모드
- 가격 추천이 작가 심리적 앵커링 효과 → 낮은 추천가로 수익 저해 가능 → "최저가 추천" 아닌 "적정 범위 추천" 명시

**KPIs**

- 가격 추천 사용률: 경매 등록 시 ≥ 50% (버튼 클릭 기준)
- 추천가 적용률: ≥ 30% (추천 클릭 → "적용" 버튼 클릭)
- 낙찰 성공률 (reserve_price 사용 시): baseline 측정 시작

---

#### K-7: AI 큐레이션 컬렉션 (Editor's Pick 자동 생성)

**Feature ID**: `ai-curation-collection`
**우선순위**: Could
**예상 기간**: ~7일
**의존성**: K-1 (ML 피드) + K-3 (AI 캡션) 완성 권장
**Booster 관계**: K-1 (ML 스코어), K-3 (캡션), Phase 7 G'-7 (admin featured), B'-5 (analytics)
**담당 agent**: bkend-expert + frontend-architect

**Goal**

주제별 AI 큐레이션 컬렉션("Editor's Pick")을 자동 생성해 컬렉터와 일반 관람자의 탐색 경험을 풍부하게 한다. "이번 주 봄의 색채", "신진 추상화 작가 5인" 등 테마 컬렉션을 자동으로 구성한다.

**Scope**

- 컬렉션 자동 생성:
  - 주제 클러스터링: K-1 임베딩 K-means 클러스터링 → 주제 자동 발견
  - LLM Gateway: 클러스터 대표 포스트들 → 컬렉션 제목 + 설명 자동 생성
  - 주 1회 자동 생성 (ai_curation_jobs.py, R-5 격리)
  - curated_collection table (alembic 0076): title, description, post_ids JSON, theme_tag, generated_at
- 노출:
  - /explore 페이지 — "이번 주 AI 큐레이션" 섹션
  - 컬렉션 상세 페이지 (/collections/{id}) — 포스트 그리드
  - 컬렉터 weekly digest email에 "추천 컬렉션" 섹션 추가 (B'-3 booster)
- admin 검토 큐:
  - 자동 생성 컬렉션 → admin 승인 후 공개 (G'-7 패턴 재사용)
  - 컬렉션 제목/설명 수동 편집 가능

**Acceptance Criteria**

- [ ] 주 1회 자동 컬렉션 생성 cron 동작
- [ ] admin 큐에서 승인/편집/거부 동작
- [ ] /explore 페이지 + 컬렉션 상세 페이지 노출 (5 locale)
- [ ] weekly digest email에 컬렉션 섹션 포함 (B'-3 booster)
- [ ] alembic 0076 green

**Risks**

- 클러스터링 품질 저하 → 주제 없는 혼합 컬렉션 생성 → admin 큐 거부율 모니터링
- LLM 제목 생성이 클리셰 반복 → 프롬프트 다양성 주입 (이전 제목 목록 포함)

**KPIs**

- 컬렉션 admin 승인율: ≥ 70% (자동 생성 품질 기준)
- 컬렉션 페이지 CTR: ≥ 10% (/explore → 컬렉션 클릭)
- 컬렉션 포스트 후원 전환율: baseline 측정 시작

---

#### K-8: ML 모델 모니터링 + A/B 테스트

**Feature ID**: `ml-monitoring-ab-test`
**우선순위**: Must
**예상 기간**: ~5일
**의존성**: K-1 (ML 피드 완성) 필수
**Booster 관계**: Phase 8 B'-5 (PostHog analytics), Phase 7 A-1 (PostHog foundation), G''-1 (OTel trace)
**담당 agent**: bkend-expert + devops-architect

**Goal**

ML 피드 v2와 기존 룰 기반 피드 v1의 성능을 PostHog Feature Flag 기반 A/B 테스트로 비교하고, ML 모델 드리프트를 자동으로 감지하는 모니터링 체계를 구축한다.

**Scope**

- A/B 테스트 (PostHog Feature Flag):
  - Flag: "ml_feed_v2" (rollout: 50% 사용자)
  - 대조군(v1): 기존 feed_scoring_jobs 룰 기반
  - 실험군(v2): K-1 ML collaborative filtering
  - 측정 metric: CTR, 체류 시간, 후원 전환율, session 길이
  - 최소 샘플: 1,000 사용자 × 2주 (통계적 유의성 95% 목표)
- ML 모델 모니터링:
  - ml_model_metrics table (alembic 0077): precision, recall, ndcg, computed_at
  - 일일 모델 성능 측정 cron (ml_monitoring_jobs.py, R-5 격리)
  - Prometheus metric: ml_precision_at_10, ml_recall_at_10, ml_ndcg
  - 성능 저하 임계치: Precision@10 < 0.10 → Slack alert (L-12 alert 패턴 재사용)
- 재학습 트리거:
  - 성능 저하 감지 → 수동 재학습 명령 또는 자동 재학습 스케줄 (OQ-7 결정)

**Acceptance Criteria**

- [ ] PostHog Feature Flag "ml_feed_v2" 생성 + 50% rollout 동작
- [ ] A/B 테스트 결과 대시보드 (PostHog experiment)
- [ ] 일일 모델 성능 측정 cron 동작
- [ ] Prometheus ml_precision_at_10 metric 수집 확인
- [ ] 성능 저하 시 Slack alert 발송 확인
- [ ] alembic 0077 green

**Risks**

- A/B 테스트 오염 (사용자 group 전환) → Feature Flag 기반 안정적 분배
- 소규모 사용자 수에서 통계적 유의성 부족 → Bayesian A/B test 방법 적용 고려 (OQ-8 결정)

**KPIs**

- A/B 테스트 통계적 유의성: p < 0.05 (2주 내 달성 목표)
- 피드 v2 CTR: v1 대비 ≥ 15% 향상 (실험군)
- 모델 모니터링 uptime: 99.9% (R-5 격리 효과)

---

## 5. Open Questions

사용자 결정 필요 항목. **"권장대로" 한 번에 수락 시 즉시 L 단계 병렬 진입 가능**.

| ID | 질문 | 옵션 | 권장 default | 근거 |
|----|------|------|:------------:|------|
| **OQ-1** | L-A 임베딩 모델 선택 | A: tuzigroup LLM Gateway (gemma4 등) / **B: sentence-transformers (로컬, 비용 0)** / C: OpenAI text-embedding-3-small | **B** | 비용 0 + 오프라인 추론 가능 + 50K events 규모에 충분. LLM Gateway는 K-3/K-5 vision 용도로 예약. sentence-transformers/all-MiniLM-L6-v2 권장 |
| **OQ-2** | L-D 테스트 DB 선택 | A: SQLite in-memory (빠름, PostgreSQL 차이 존재) / **B: PostgreSQL test DB (실제 환경 동일)** / C: Docker PostgreSQL per-test | **B** | Phase 8 report §7 lesson: "실제 DB 테스트 → mock/prod divergence 방지". PostgreSQL test DB는 CI에서 이미 운영 중 |
| **OQ-3** | L-E WCAG AAA 범위 | A: 전체 페이지 / **B: 핵심 3페이지 (피드/포스트/경매) AAA** / C: 색상 대비만 | **B** | 비용 대비 효과 — 핵심 3페이지 집중. 전체 AAA는 브랜드 컬러 전면 수정 필요, 리스크 과도 |
| **OQ-4** | K-1 ML 모델 선택 | **A: Matrix Factorization (implicit 라이브러리, 구현 빠름)** / B: Two-Tower (정확도 높음, 구현 복잡) / C: LightFM (hybrid) | **A** | 50K events 규모에서 Matrix Factorization이 충분. Two-Tower는 100K+ events 이후 고려. 구현 속도 우선 — Phase 9 K 단계 10주 내 완성 목표 |
| **OQ-5** | K-2 Diversity 가중치 λ | A: λ=0.1 (ML 스코어 90% 반영) / **B: λ=0.3 (균형)** / C: λ=0.5 (다양성 50%) | **B** | K-8 A/B 테스트로 검증하기 전 기본값. 개인화 vs 다양성 균형. Phase 9 K-8 A/B로 최적값 탐색 후 조정 |
| **OQ-6** | K-5 LLM 도슨트 TTS | **A: 구현 안 함 (브라우저 Web Speech API만 선택)** / B: 브라우저 Web Speech API 기본 내장 / C: AWS Polly (품질 높음, 비용 발생) | **A** | Phase 9 scope 초과. TTS는 Phase 10 별도 PDCA. 도슨트 텍스트 품질 먼저 안정화 |
| **OQ-7** | K-8 ML 재학습 방식 | **A: 수동 재학습 (admin 명령)** / B: 자동 재학습 (성능 저하 감지 시) / C: 주 1회 정기 재학습 | **A** | 초기 단계에서 자동 재학습은 위험 (데이터 품질 모니터링 없이 재학습 시 성능 저하 가능). 수동 승인 후 재학습이 안전. Phase 10에서 자동화 검토 |
| **OQ-8** | K-8 A/B 테스트 방법 | **A: Frequentist (p < 0.05, 2주 고정)** / B: Bayesian (샘플 적어도 유의) / C: Multi-armed bandit (동적 할당) | **A** | PostHog 기본 제공 Frequentist A/B 활용. Bayesian/MAB는 추가 구현 필요. Phase 9 단순화 우선 |
| **OQ-9** | K-3 AI 캡션 LLM 모델 | **A: tuzigroup LLM Gateway (gemma4 vision, 사내 인프라)** / B: OpenAI GPT-4o Vision / C: Google Gemini Vision | **A** | 사내 인프라 우선 (Phase 7부터 검증된 tuzigroup Gateway). 비용 최소화. 품질 부족 시 B 검토 |
| **OQ-10** | L-C DM Group 최대 인원 | A: 10인 / **B: 50인** / C: 100인 / D: 무제한 | **B** | 팬클럽/스터디 그룹 용도에 50인 적절. 100인+ 시 WebSocket broadcast 부하 급증. 추후 확장 가능 |
| **OQ-11** | Phase 9 시작 트리거 | **A: Phase 8 archive 완료 확인 후 즉시 (alembic 0065 기준)** / B: 사용자 결정 대기 / C: L 단계만 먼저 진행 | **A** | Phase 5/6/7/8 동일 패턴. alembic current → 0065 확인 후 즉시 L 단계 병렬 진입 |
| **OQ-12** | Phase 9 K 단계 ML 호스팅 | **A: 자체 ECS (Python inference 서버, 비용 ↓)** / B: AWS SageMaker (managed, 비용 ↑) / C: Hugging Face Inference Endpoints | **A** | Phase 8 G''-2 ECS 인프라 재사용. SageMaker 초기 비용 $0.10~0.20/hr 과도. sentence-transformers 로컬 추론 = ECS에서 충분히 가능 |
| **OQ-13** | L 단계 진행 방식 | A: 6개 sub-PDCA 순차 / **B: L-A + L-D 선결 → L-B + L-C + L-E + L-F 4개 병렬** / C: 전체 동시 병렬 | **B** | L-A (임베딩 인프라)는 K 단계 Critical Path → 먼저 착수. L-D (테스트 refactor)는 L-C DM 안정화 후 진행. 나머지 4개는 독립 병렬 가능 |

---

## 6. Acceptance Criteria (Phase 9 종료 기준)

| ID | 기준 | 검증 방법 |
|----|------|----------|
| **AC-1** | L 단계 6개 sub-PDCA (L-A~L-F) 모두 archived | `.pdca-status.json` L-A~L-F phase="archived" |
| **AC-2** | K 단계 8개 sub-PDCA (K-1~K-8) 모두 archived | `.pdca-status.json` K-1~K-8 phase="archived" |
| **AC-3** | Phase 8 carry-over 13건 모두 청산 매핑 | Phase 9 §2 carry-over 매핑표 13건 ✅ |
| **AC-4** | 각 sub-PDCA Match Rate ≥ 90% (목표 평균 ≥ 95%) | 개별 analysis.md matchRate 필드 |
| **AC-5** | Tests: 412 → 419+ passed (L-D refactor 7개 복구), skipped = 0 | pytest 결과 |
| **AC-6** | ML 피드 v2 A/B 테스트 결과: CTR ≥ 15% 향상 (p < 0.05) | PostHog A/B experiment |
| **AC-7** | AI 캡션 적용 포스트 ≥ 50건 (K-3 실제 운영) | posts.caption_generated_at 비null 건수 |
| **AC-8** | Group DM 정상 동작 (3인 이상 대화 1건) | DB group_conversations 확인 |
| **AC-9** | WebSocket 실시간 메시지 전달 지연 ≤ 100ms (p95) | Prometheus ws_latency metric |
| **AC-10** | Lighthouse performance ≥ 90 (L-A 번들 완성) | Lighthouse CI |
| **AC-11** | Newsletter open rate 측정 시작 (L-B open rate tracking) | DB newsletter_open_events 건수 ≥ 10 |
| **AC-12** | Featured Artist 자동 선정 cron 동작 (신진작가 ≥ 70%) | DB featured_artist_weekly 확인 |
| **AC-13** | tsc 0 에러, 회귀 없음 | CI pipeline 자동 |
| **AC-14** | alembic 0066~0077 (12 신규 마이그레이션) 무결 | alembic upgrade/downgrade 테스트 |
| **AC-15** | R-5 cron 격리 일관 — Phase 9 신규 cron workers 모두 격리 패턴 적용 | 코드 리뷰 확인 |
| **AC-16** | 5 locale(ko/en/ja/zh/es) i18n — Phase 9 신규 feature 동시 5 locale | locale parity 검증 |

---

## 7. Wave 병렬 위임 전략

Phase 5/6/7/8과 동일한 wave-based delegation (최대 5 agents 동시).

### L 단계 — Wave 계획 (OQ-13 B 권장 기준)

```
L Wave 1 [2개 동시, Day 1~5]:
  ├─ [bkend-expert]       L-A: ML 임베딩 파이프라인 (alembic 0066 + embedding cron)
  └─ [frontend-architect] L-A: 번들 최적화 완성 (Konva.js + Lighthouse ≥ 90)

L Wave 2 [4개 동시, Day 6~14]:
  ├─ [bkend-expert]       L-B: RSS + OG + open rate (3종, alembic 0067)
  ├─ [bkend-expert]       L-C: Group DM + WebSocket + 파일 첨부 (alembic 0068~0069)
  ├─ [frontend-architect] L-E: WCAG AAA + cognitive a11y (alembic 0070)
  └─ [bkend-expert]       L-F: 번역 메모리 + cohort 알림 (alembic 0071~0072)

L Wave 3 [1개, Day 15~17]:
  └─ [bkend-expert]       L-D: Over-mocked test refactor (L-C 안정화 후)

Milestone: L 종결 (3~4주) — carry-over 13건 청산 + 임베딩 인프라 완성
```

### K 단계 — Wave 계획

```
K Wave 1 [1개 단독, Week 5~6]:
  └─ [bkend-expert]       K-1: Collaborative filtering 피드 v2 (Critical Path)

K Wave 2 [3개 동시, Week 7~8]:
  ├─ [bkend-expert]       K-2: Diversity reranking (K-1 의존)
  ├─ [bkend-expert]       K-3: AI 작품 자동 캡션 (독립, alembic 0073)
  └─ [bkend-expert]       K-4: AI Featured Artist 추천 (alembic 0074)

K Wave 3 [3개 동시, Week 9~10]:
  ├─ [bkend-expert]       K-5: LLM 도슨트 (K-3 기반, alembic 0075)
  ├─ [bkend-expert]       K-6: AI 가격 추천 (독립)
  └─ [bkend-expert]       K-7: AI 큐레이션 컬렉션 (K-1 기반, alembic 0076)

K Wave 4 [1개, Week 11~12]:
  └─ [devops-architect]   K-8: ML 모니터링 + A/B 테스트 (K-1 완성 후, alembic 0077)

K Wave 5 [검증 + 아카이브, Week 13~14]:
  └─ [bkend-expert]       전체 KPI 측정 + A/B 결과 확인 + Phase 9 아카이브
```

### Agent 역할 매핑

| Agent | 담당 | Phase 9 주요 작업 |
|-------|------|-----------------|
| bkend-expert | 백엔드 | L-A/B/C/D/F, K-1~K-8 백엔드 전반 |
| frontend-architect | 프론트엔드 | L-A 번들, L-E a11y, K-3/K-4/K-5/K-7 UI |
| devops-architect | 인프라 | K-8 ML 모니터링 + Prometheus + Slack alert |
| security-architect | 보안 검토 | L-C WebSocket 보안 + K-3 LLM prompt injection 방어 |

---

## 8. KPI 정의

Phase 9 종결 시 측정할 핵심 성과 지표.

| KPI | 측정 도구 | Phase 8 Baseline | Phase 9 목표 | 담당 sub-PDCA |
|-----|----------|:---------------:|:------------:|:------------:|
| **ML 피드 CTR** | PostHog A/B | 측정 미시작 | ≥ 15% 향상 (v2 vs v1) | K-1, K-8 |
| **신진작가 발굴율** | PostHog | 미측정 | 피드 상위 20개 중 ≥ 30% 팔로워 < 100 | K-2, K-4 |
| **AI 캡션 채택율** | DB 기반 | 0% | ≥ 60% (수정 없이 사용) | K-3 |
| **도슨트 페이지 체류 시간** | PostHog | 미측정 | ≥ 40% 증가 | K-5 |
| **경매 가격 추천 사용률** | PostHog | 0% | ≥ 50% (경매 등록 중 버튼 클릭) | K-6 |
| **컬렉션 CTR** | PostHog | 0% | ≥ 10% (/explore → 컬렉션) | K-7 |
| **A/B 테스트 유의성** | PostHog Experiments | N/A | p < 0.05 (2주 내) | K-8 |
| **ML 모델 Precision@10** | Prometheus | 측정 미시작 | ≥ 0.15 | K-1, K-8 |
| **Tests passed** | pytest | 412 | ≥ 419 (7개 복구) | L-D |
| **Lighthouse performance** | Lighthouse CI | 86 | ≥ 90 | L-A |
| **Initial bundle size** | next/bundle-analyzer | 198KB | ≤ 180KB | L-A |
| **WebSocket 메시지 지연** | Prometheus | 340ms (polling) | ≤ 100ms | L-C |
| **번역 캐시 hit rate** | DB + Redis | 0% | ≥ 60% (14일 후) | L-F |
| **Newsletter open rate** | DB pixel tracking | 38% (Phase 8 estimate) | 실제 픽셀 측정 시작 | L-B |
| **Cohort D7 retention** | PostHog | 71% (Phase 8) | ≥ 73% (ML 피드 효과) | K-1, K-8 |

---

## 9. Risks & Mitigation

| Risk | 영향 | 가능성 | 완화 방안 |
|------|:----:|:------:|----------|
| **ML 학습 데이터 부족** — 50K events가 Matrix Factorization에 부족할 수 있음 | High | Medium | K-1: Precision@10 < 0.10 시 인기도 가중치 blend fallback (Popularity Bias 보완). 모델 단순화 먼저 시도 후 Two-Tower로 업그레이드 |
| **LLM Gateway 비용 폭증** — K-3 캡션 + K-5 도슨트 동시 운영 시 API 비용 급증 | High | Medium | 포스트당 일일 요청 제한 (캡션 3회, 도슨트 2회). L-11 번역 메모리 캐시로 번역 비용 60% 절감. 월간 비용 모니터링 dashboard |
| **A/B 테스트 통계적 유의성 미달** — 사용자 수 부족으로 2주 내 p < 0.05 불가 | Medium | High | OQ-8 A 기준: 최소 1,000 사용자 × 2주 확보 전략 필요. 사용자 부족 시 Bayesian 방법 전환 (OQ-8 재협의) |
| **WebSocket 다중 인스턴스 broadcast 누락** — L-C ECS 다중 인스턴스 배포 시 | High | Medium | Redis pub/sub (G''-2 booster) 필수 구현. 단일 인스턴스 시 문제 없음, 스케일아웃 전 pub/sub 테스트 |
| **alembic 충돌** — 0066~0077 병렬 개발 시 revision 충돌 | Medium | Medium | Phase 6/7/8 패턴: revision ID 사전 배정표 완성. `alembic heads` 자동 감지 CI 통합 |
| **Group DM 스팸/어뷰징** — 대규모 그룹 생성 후 스팸 발송 | High | Medium | L-C: rate limit (5 messages/min/user/group) + report/block UI + admin 모더레이션 큐. 그룹 생성 최대 10개/user 제한 |
| **AI 캡션 품질 불균일** — 추상화/비구상 작품에서 설명 품질 저하 | Medium | High | K-3: 장르 태그 기반 프롬프트 조정 + "AI 생성" 투명성 문구 + 작가 수정 가능 → 책임 문제 완화 |
| **번역 메모리 캐시 무효화** — tuzigroup 모델 변경 시 이전 캐시 품질 저하 | Low | Medium | L-F: model 버전 필드 관리 (model_version 컬럼) + 모델 변경 시 cache invalidation 자동 실행 |
| **K-6 가격 추천 데이터 부족** — 초기 낙찰 데이터 적어 추천 품질 저하 | Medium | High | K-6: 낙찰 데이터 < 100건 시 장르 배수만 사용하는 fallback 모드 + "데이터 축적 중" 안내 |
| **L-D 테스트 refactor 회귀** — 기존 412 tests 일부 실패 가능 | Medium | Low | L-C 완성 후 L-D 진행 (DM 모델 안정화 선결). 각 테스트 unit → integration 전환 시 isolation 패턴 (`@pytest.fixture(scope="function") + rollback`) 엄격 적용 |

---

## 10. Timeline & Milestones

```
Phase 9 총 13~14주 (L 단계 3~4주 + K 단계 10주)

Week 1~4 — L: Carry-over Consolidation
┌─────────────────────────────────────────────────────────────────────┐
│ Week 1~2 [Wave 1+2 동시]:                                           │
│   L-A: ML 임베딩 인프라 + 번들 최적화 (alembic 0066)               │
│   L-B: RSS + OG + open rate (alembic 0067) [병렬]                   │
│   L-C: Group DM + WebSocket + 파일 첨부 (alembic 0068~0069) [병렬] │
│   L-E: WCAG AAA + cognitive a11y (alembic 0070) [병렬]              │
│   L-F: 번역 메모리 + cohort 알림 (alembic 0071~0072) [병렬]         │
│ Week 3 [Wave 3]:   L-D over-mocked test refactor                    │
│ Week 4 [마무리]:   L KPI 측정 + carry-over 13건 청산 확인           │
│ Milestone: L 종결 — 6 sub-PDCAs archived + 임베딩 인프라 완성 ✅     │
└─────────────────────────────────────────────────────────────────────┘

Week 5~6 — K Wave 1: ML Feed v2 Critical Path
┌─────────────────────────────────────────────────────────────────────┐
│ Week 5~6 [단독]:   K-1 collaborative filtering 피드 v2              │
│                    (Matrix Factorization + 추론 서비스 + Redis 캐시) │
│ Milestone: K-1 archived → K Wave 2 병렬 진입 준비 ✅                │
└─────────────────────────────────────────────────────────────────────┘

Week 7~8 — K Wave 2: AI 기능 3종 병렬
┌─────────────────────────────────────────────────────────────────────┐
│ Week 7~8 [병렬]:   K-2 diversity reranking                          │
│                    + K-3 AI 캡션 자동 생성 (alembic 0073)           │
│                    + K-4 AI Featured Artist (alembic 0074)          │
│ Milestone: K-2/3/4 archived ✅                                       │
└─────────────────────────────────────────────────────────────────────┘

Week 9~10 — K Wave 3: LLM 고도화 3종 병렬
┌─────────────────────────────────────────────────────────────────────┐
│ Week 9~10 [병렬]:  K-5 LLM 도슨트 (alembic 0075)                   │
│                    + K-6 AI 가격 추천                                │
│                    + K-7 AI 큐레이션 컬렉션 (alembic 0076)          │
│ Milestone: K-5/6/7 archived ✅                                       │
└─────────────────────────────────────────────────────────────────────┘

Week 11~14 — K Wave 4+5: ML 모니터링 + A/B 검증
┌─────────────────────────────────────────────────────────────────────┐
│ Week 11~12 [단독]: K-8 ML 모니터링 + A/B 테스트 세팅 (alembic 0077) │
│ Week 13~14 [검증]: A/B 2주 운영 → 통계적 유의성 확인                │
│                    전체 KPI 측정 + Phase 9 아카이브                  │
│ Milestone: Phase 9 종결 — 14/14 sub-PDCAs archived ✅               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. Dependencies & Phase 8 Carry-over Mapping (최종)

Phase 8 report.md §9 carry-over 13건 → Phase 9 L 단계 100% 흡수 매핑:

| # | Phase 8 Carry-over | Phase 8 §9 우선순위 | Phase 9 매핑 | 처리 방식 |
|---|-------------------|:-----------------:|:----------:|----------|
| 1 | G''-6 frontend-bundle-optimization | High | **L-A** | Lighthouse ≥ 90 + bundle ≤ 180KB 최종 완성 |
| 2 | H'-6 ML feed v2 prep (RSS auto-fetch) | Medium | **L-A + L-B** | 임베딩 파이프라인(L-A) + RSS auto-fetch(L-B) 분리 구현 |
| 3 | pg_trgm fuzzy search DB extension | Low | **Phase 10+** | DBA 승인 + DB 마이그레이션 위험도 — Phase 10 인프라 PDCA |
| 4 | /metrics 포트 분리 + Bearer rotation | Low | **Phase 10+** | Prometheus 이미 production-ready. 보안 감사 PDCA 별도 |
| 5 | DM Group 메시징 (1:1→N:N) | High | **L-C** | Group DM + WebSocket + 파일 첨부 통합 구현 |
| 6 | WebSocket 실시간 Push | Medium | **L-C** | L-C에 WebSocket 통합 |
| 7 | File/Image attachment DM | Medium | **L-C** | L-C에 파일 첨부 통합 |
| 8 | Over-mocked test refactor (7개) | Low | **L-D** | DMConversation/DeviceToken/NotificationPreferences 7개 skip 정상화 |
| 9 | Mobile native app | High | **Phase 10+** | Flutter/React Native — Phase 9 ML 완성 후 진입 |
| 10 | AI 작가 featured 큐레이션 | Low | **K-4** | AI Featured Artist 추천으로 Phase 9에서 직접 구현 |
| 11 | Newsletter open rate 수집 | Medium | **L-B** | 1x1 픽셀 + click tracking 구현 |
| 12 | B2B 리포트 (갤러리/학교) | Very Low | **Phase 10+** | 파트너십 체결 후. Phase 10 이상 |
| 13 | Real-time collaborative editing | Very Low | **Phase 10+** | 복잡도 + 인프라 비용. Phase 10 재평가 |

**Phase 9 흡수 (10건)**: L-A(1+2) + L-B(2+11) + L-C(5+6+7) + L-D(8) + K-4(10)
**Phase 10+ defer (3건)**: pg_trgm + /metrics 포트 분리 + Mobile native + B2B 리포트 + collaborative editing (Phase 8 §9 Very Low 우선순위 3건 유지)

---

## 12. Alembic Migration 사전 배정

| 번호 | 마이그레이션 | 담당 sub-PDCA | 내용 |
|:----:|------------|:------------:|------|
| **0066** | user_embedding + item_embedding | L-A | ML 임베딩 테이블 2종 |
| **0067** | rss_source | L-B | RSS 소스 관리 테이블 |
| **0068** | group_conversations + group_participants | L-C | Group DM 테이블 2종 |
| **0069** | message_attachments | L-C | DM 파일 첨부 테이블 |
| **0070** | users.simple_mode | L-E | 단순 모드 UserPreference |
| **0071** | translation_cache | L-F | LLM 번역 메모리 |
| **0072** | alert_history | L-F | Cohort 알림 중복 방지 |
| **0073** | posts.caption_text + caption_generated_at | K-3 | AI 캡션 필드 |
| **0074** | featured_artist_weekly | K-4 | 주간 추천 신진작가 |
| **0075** | posts.docent_text + docent_generated_at | K-5 | LLM 도슨트 필드 |
| **0076** | curated_collection | K-7 | AI 큐레이션 컬렉션 |
| **0077** | ml_model_metrics | K-8 | ML 모델 성능 이력 |

**Phase 8 마지막**: alembic 0065 (Phase 8 완료 기준)
**Phase 9 신규**: 0066~0077 (12건)

---

## 13. README 비즈니스 비전 매핑

| README 비전 문장 | Phase 9 sub-PDCA | 구체적 구현 |
|-----------------|:----------------:|-----------|
| **"AI 세상으로 가면 갈수록 예술가들이 제일 먼저 굶어 죽음"** | **K-3 + K-5 + K-6** | AI 캡션으로 작품 가치 자동 증폭. LLM 도슨트로 스토리텔링 자동화. AI 가격 추천으로 경매 수익 최적화 — 작가가 AI를 활용해 경제적 생존 가능 |
| **"전 세계 아티스트들의 인덱스를 만들고 싶음"** | **K-1 + K-4 + K-7** | ML collaborative filtering으로 신진작가 자동 발굴. AI Featured Artist 추천으로 주간 글로벌 작가 인덱싱. AI 큐레이션 컬렉션으로 테마별 작가 묶음 — 알고리즘이 글로벌 신진작가를 능동적으로 인덱싱 |
| **"유저들이 늘어나야 소비자들도 늘어남" — 그로스해킹** | **K-1 + K-2 + K-8** | ML 피드 개인화 CTR ≥ 15% 향상. Diversity reranking으로 신규 작가 발굴 → 후원자 유입 다변화. A/B 테스트로 그로스 효과 측정 |
| **"히스토리를 두세 개 만든다" — 성공 사례 스토리텔링** | **K-3 + K-5** | AI 캡션 + LLM 도슨트 = 작품마다 자동 스토리 생성. "남미 페루 대학생 여학생" 같은 사례를 AI가 스토리로 자동 포장 → 언론/SNS 확산 콘텐츠 자동 생성 |
| **"동유럽이든 남미든 동아시아든 엄청난 꿈과 희망"** | **L-11 + K-4** | 번역 메모리로 LLM 번역 비용 ↓ → 더 많은 언어 AI 해설 가능. AI Featured Artist 추천이 지역 다양성 보정 → 개발도상국 신진작가 글로벌 노출 기회 |
| **"후원 개념을 넣고 후원할 수 있는 구조를 만듦"** | **K-1 + K-6 + K-8** | ML 피드 → 더 많은 신진작가-후원자 매칭. AI 가격 추천 → 경매 낙찰률 ↑ → 작가 수익 구조 강화. A/B 테스트 → 후원 전환율 과학적 측정 |

---

## 14. Phase 10 검토 후보

Phase 9 종료 후 다음 로드맵 옵션.

| 항목 | Phase 9 defer 이유 | Phase 10 조건 | 예상 우선순위 |
|------|:----------------:|:-------------|:------------:|
| **Mobile Native App** (Flutter/React Native) | 웹 안정화 + ML 완성 우선 | Phase 9 K 단계 완성 + 사용자 1만 명 달성 | High |
| **WebSocket → gRPC 전환** | L-C WebSocket 구현 후 검토 | 동시 접속 1만 명 이상 시 필요 | Medium |
| **pg_trgm Fuzzy Search** | DBA 승인 + Phase 9 집중 | PostgreSQL DBA 검토 후 | Low |
| **B2B Gallery 파트너십** | 파트너십 영업 선행 필요 | 갤러리 파트너 계약 체결 후 | Medium |
| **NFT 연동** | 기술 성숙도 + 시장 수요 검증 | Web3 지갑 통합 결정 후 | Low |
| **ML 모델 AutoML** | K-1 Matrix Factorization 안정화 후 | Precision@10 ≥ 0.20 달성 후 Two-Tower 검토 | Medium |
| **/metrics 포트 분리 + Bearer rotation** | Phase 9 집중 | 보안 감사 일정 확정 후 | Low |
| **Real-time Collaborative Editing** | 인프라 비용 + 복잡도 | 사용자 수요 확인 후 | Very Low |
| **LLM 도슨트 TTS** (AWS Polly) | Phase 9 scope 초과 | K-5 도슨트 품질 안정화 후 | Medium |
| **컬렉터 전용 리포트** (갤러리 파트너용) | B2B 파트너십 선행 | B2B 계약 후 | Low |

---

## 15. Phase 5~8 Lessons Applied (Phase 9 적용 방침)

| 학습 사항 | Phase 9 적용 방식 |
|----------|-----------------|
| **권장 default 일괄 수락 패턴** (Phase 5~8 OQs 모두 권장 채택, 협상 라운드 0) | Phase 9 OQ-1~OQ-13 동일 표 형식 + 권장 default 명시. "권장대로" 응답 시 즉시 L Wave 1 진입 |
| **Wave 기반 병렬 위임** (최대 5 agents 동시, 시간 단축 ~40%) | L Wave 1~3 + K Wave 1~5 = 총 5 wave. L Wave 2에서 4개 동시 병렬 (최대 5 agents 기준) |
| **alembic revision ID 충돌 방지** | Phase 9 사전 배정 완성 (0066~0077, 12건). `alembic heads` 자동 감지 CI |
| **R-5 cron 격리 표준** (Phase 5→8 누적 11 workers, 100% 격리) | Phase 9 신규 cron workers (embedding_compute_jobs, rss_feed_jobs, weekly_featured_jobs, ai_curation_jobs, ml_monitoring_jobs, cohort_alert_jobs) 모두 R-5 격리 적용 |
| **Mock 모드 fallback** (OTEL/Redis/FCM/SES 모두 Mock 지원) | K-1 ML 서비스: ML_ENABLED=false → 인기도 기반 fallback. K-3 캡션: LLM_GATEWAY_URL 미설정 → 수동 입력 안내 |
| **Critical Path 명확화** | K-1 ML 피드 v2가 K-2/K-4/K-7/K-8의 의존성 → K Wave 1 단독 선결 필수 |
| **Booster 패턴 재사용** | K-3 캡션 → H'-1 alt text booster. K-4 → G'-7 admin featured 대체. L-F → B'-5 cohort dashboard booster. L-C → B'-2 DM booster |
| **i18n namespace 엄격 분리** | Phase 9 신규 namespace 사전 배정: `mlFeed.*` `aiCaption.*` `docent.*` `featuredArtist.*` `priceRecommend.*` `curation.*` `groupDm.*` `simpleMode.*` |

---

## 16. 다음 액션

### Phase 9 시작 전 체크리스트

1. **alembic current → 0065 확인** (OQ-11=A 권장 — Phase 8 완료 기준)
2. **OQ-1~OQ-13 결정** — "권장대로" 일괄 수락 시 즉시 L Wave 1+2 병렬 진입
3. **Embedding 모델 다운로드** (OQ-1=B 채택 시: `pip install sentence-transformers`)
4. **alembic revision ID 사전 배정 확인** (0066~0077 = 12건)
5. **PostHog Feature Flag 생성** (K-8: "ml_feed_v2" flag 사전 생성 권장)

### L 단계 진입 명령 (OQ-13=B 권장 기준)

```bash
# Wave 1: L-A Critical Path 먼저
/pdca plan ml-embedding-infra-bundle-final         # L-A

# Wave 2: 4개 동시 병렬 (L-A 착수 후 바로)
/pdca plan external-content-booster                # L-B
/pdca plan dm-expansion                            # L-C
/pdca plan wcag-aaa-accessibility                  # L-E
/pdca plan translation-memory-cohort-alert         # L-F

# Wave 3: L-C 완료 후
/pdca plan test-quality-refactor                   # L-D
```

### K 단계 진입 명령 (L 완료 후)

```bash
# Wave 1: K-1 단독 선결 (Critical Path)
/pdca plan ml-feed-collaborative-filtering          # K-1

# Wave 2: K-1 완료 후 병렬
/pdca plan feed-diversity-reranking                 # K-2
/pdca plan ai-artwork-caption                       # K-3
/pdca plan ai-featured-artist                       # K-4

# Wave 3: K-2/3/4 완료 후 병렬
/pdca plan llm-docent-artwork                       # K-5
/pdca plan ai-price-recommendation                  # K-6
/pdca plan ai-curation-collection                   # K-7

# Wave 4: K-1 완료 후 (K-2/3/4와 병렬 가능)
/pdca plan ml-monitoring-ab-test                    # K-8
```

---

## 17. 결정 기록 (Decisions Log)

### 2026-05-05 — Phase 9 로드맵 초안 (product-manager)

| 결정 | 내용 | 근거 |
|------|------|------|
| Phase 9 구조 | L(3~4주) → K(10주) = 총 13~14주 순차 | 사용자 선택: L(carry-over) 먼저 → K(ML/AI) 순차 |
| L 단계 sub-PDCAs | 6개 그룹 (L-A~L-F) | Phase 8 carry-over 13건 → 그룹화로 효율화 |
| K 단계 sub-PDCAs | 8개 (K-1~K-8) | README AI 비전 + 그로스해킹 고도화 |
| K-1 ML 모델 | Matrix Factorization (OQ-4=A 권장) | 50K events 규모에서 충분. 빠른 구현 우선 |
| L-A 임베딩 모델 | sentence-transformers 로컬 (OQ-1=B 권장) | 비용 0 + tuzigroup Gateway는 vision 용도 예약 |
| K-3/K-5 LLM | tuzigroup LLM Gateway (OQ-9=A 권장) | 사내 인프라 우선. Phase 7부터 검증 완료 |
| ML 호스팅 | 자체 ECS (OQ-12=A 권장) | Phase 8 G''-2 ECS 인프라 재사용. SageMaker 비용 과도 |
| alembic 배정 | 0066~0077 (12건) | Phase 8 종료 0065 기준 + Phase 9 12건 사전 배정 |
| L Wave 전략 | L-A 먼저 + L-B/C/E/F 병렬 + L-D 마지막 | L-A Critical Path (K 단계 의존). L-D는 L-C 안정화 후 |
| K Critical Path | K-1 단독 선결 | K-2/K-4/K-7/K-8 모두 K-1 의존 |
| Phase 10 scope | Mobile + pg_trgm + B2B 제외 | Phase 9 ML/AI 집중. scope 경계 명확화 |

---

## Version History

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|---------|--------|
| 0.1 | 2026-05-05 | Phase 9 로드맵 초안. L(6 sub-PDCA) + K(8 sub-PDCA) = 14 sub-PDCAs. 13 OQs (권장 default 포함). Phase 8 carry-over 13건 매핑 §11. README 비전 매핑 §13. alembic 0066~0077 사전 배정 §12. Wave 병렬 전략 §7. Phase 10 후보 §14. | itpe-ince (Claude Sonnet 4.6 / product-manager) |
