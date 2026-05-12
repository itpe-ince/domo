---
template: plan
version: 1.2
feature: editor-revamp-roadmap
date: 2026-04-29
author: itpe-ince (Claude Opus 4.7)
project: domo
version: v1
status: Draft (Roadmap)
---

# 에디터 전면 개편 — 로드맵 (Master Plan)

> **Summary**: 포스트 에디터(`/posts/new`)의 입력 흐름·콘텐츠 풍부도·발행 옵션·작가 도구를 전면 개편하고, 발행 옵션과 작가 기능에 대한 시스템 차원(스키마·API·노출 정책) 대응까지 동반한다.
>
> **Project**: domo (v1)
> **Author**: itpe-ince
> **Date**: 2026-04-29
> **Status**: Roadmap (Sub-PDCA 들의 인덱스. 각 항목은 별도 plan 문서로 본격 진입)

---

## 0. 개편 배경 & 목표

현재 에디터는 [v1/frontend/src/app/posts/new/page.tsx](../../../frontend/src/app/posts/new/page.tsx) 단일 474줄 컴포넌트로 7개 sub-component를 조합한 폼이다. MVP 수준의 입력 폼은 갖추었으나 다음 한계가 있다:

- **임시 저장 부재** — 글 작성 중 페이지 이탈 시 전부 손실
- **반응형 한계** — 모바일/데스크탑 동일 레이아웃, 공간 활용 비효율
- **미디어 관리 빈약** — 순서 변경 불가, 진행률 미표시, 캡션 못 달음, 사후 편집 없음
- **본문 빈약** — 마크다운/링크/굵게 같은 기본 서식 없음
- **메타데이터 입력 자유 텍스트** — `dimensions/medium/year` 일관성 없음
- **발행 옵션 빈약** — 공개 범위/댓글/시리즈/예약발행 등 시스템 차원 옵션 없음
- **작가 도구 부재** — 가격 가이드/우선 공개/홍보 도구 등 작가 친화 기능 없음
- **권한 게이트 약함** — 작가 아닌 사용자도 product 폼은 보임 (submit 시점에만 차단)

본 로드맵은 위 항목 전부를 11개 독립 PDCA 사이클로 분해하고, 의존성과 영향도를 고려해 4단계로 실행한다.

---

## 1. 요구사항 원본 (사용자 입력 — 변형 금지 보존)

### A. 메이킹 영상 토글
- 메이킹 영상 올리는 **별도 모달** 구성, 해당 모달을 통해 메이킹 영상 제작 및 편집
- **사후 토글**을 선택하면, 메이킹 영상 제작 편집 모달이 열림

### B-1. 입력 흐름 (UX)
- 작가가 아닌 경우에는 **상품 포스트 불가** 여야 함
- 글 작성 중 **임시 저장** 기능 필요
- **모바일과 데스크탑 에디터 영역의 디자인 분리** 필요
- 미디어 순서 조절 **드래그**로 변경 가능해야 함
- 여러 파일 업로드 시 **각 파일별 진행률 표시** 필요
- **글 길이 제한/카운터** 필요

### B-2. 콘텐츠 풍부도
- 본문에 **마크다운 / 굵게 / 링크** 같은 서식 필요
- 이미지에 **캡션/설명 등록** 가능해야 함
- **이미지 에디터**(회전, 크롭, 모자이크, 워터마크), **영상 에디터**(영상 잘라내기, 썸네일 선택) 제공 필요
- 작품 메타데이터(`dimensions`/`medium`/`year`) 입력에 대한 **데이터 유형별 입력** 제공 필요
- **공동 작가/협업자 태그** 등록 필요

### B-3. 발행 옵션
- **공개 범위** (전체/팔로워/링크만) 선택 기능 필요
- **댓글 허용/비허용** 기능 필요
- **작품 카탈로그(시리즈) 묶기** 기능 필요
- **예약 발행** 기능 필요

### B-4. 작가 기능
- **가격 책정 보조** (시세 가이드, 추천 시작가) 제공 필요
- **후원자/단골에게 먼저 공개** 옵션 제공 필요
- **옥션 종료 알림/홍보 도구** 제공 필요

### C. 화면 UI 개선
- 우선 **에디터만 개선** 필요
- 에디터에서 선택한 **발행 옵션, 작가 기능에 대한 시스템 적인 대응** 필요

---

## 2. 11개 Sub-PDCA — 그룹화 & 실행 단계

### Phase 1 — Foundation (구조/안전망)

| # | Feature | 다루는 요구사항 | 예상 규모 | 비고 |
|---|---|---|---|---|
| 1 | `editor-role-gating` | B-1 (작가 아니면 상품 불가) | XS (반나절) | UI 차원 강화 — 현재 submit 시 차단만 됨. type 선택 자체를 게이트 |
| 2 | `editor-draft-autosave` | B-1 (임시 저장) | M (2~3일) | localStorage + 서버 draft 컬럼 (Post.status=draft 활용 가능) |
| 3 | `editor-responsive-redesign` | B-1 (모바일/데스크탑 분리) + C (UI 개선) | L (1주) | 데스크탑 2-pane (작성+미리보기) / 모바일 풀스크린 단계형 |

### Phase 2 — Media & Content (콘텐츠 표현력)

| # | Feature | 다루는 요구사항 | 예상 규모 | 비고 |
|---|---|---|---|---|
| 4 | `editor-media-ux` | B-1 (드래그 순서, 파일별 진행률), B-2 (이미지 캡션) | M (3~4일) | dnd-kit 도입, 업로드 동시성 표시, MediaAsset.caption 컬럼 추가 |
| 5 | `editor-rich-content` | B-2 (마크다운/굵게/링크), B-1 (글자수 카운터) | M (2~3일) | tiptap 또는 marked + sanitize, 본문 mode 토글 (plain/rich) |
| 6 | `editor-media-studio` | A (메이킹 모달), B-2 (이미지/영상 에디터) | XL (2주+) | 가장 큼. cropper.js + ffmpeg.wasm or 서버 사이드 처리 결정 필요 |
| 7 | `editor-product-meta` | B-2 (메타데이터 유형별 입력, 협업자 태그) | M (3~4일) | dimensions(WxHxD 분리), medium(enum+자유), year(연도 picker), 협업자 user search |

### Phase 3 — Publishing System (시스템 차원 대응)

| # | Feature | 다루는 요구사항 | 예상 규모 | 비고 |
|---|---|---|---|---|
| 8 | `publish-controls` | B-3 전체 (공개범위, 댓글, 시리즈, 예약발행) | L (1.5주) | DB 마이그레이션 4개. Post.visibility / Post.comments_enabled / Series 신규 모델 / Post.scheduled_at(이미 있음) |
| 12 | `notifications-ux-audit` | 사용자 아이콘 N뱃지, 사용자 메뉴 알림 항목, 알림 카드 다중 deep link, read 상태 시각화 | M (3~4일) | 추가 2026-04-29 (사용자 우려 반영). 알림 시스템 전반 UX 일관성 — Phase 3 시스템 차원 작업 |

### Phase 4 — Artist Tools (작가 친화 기능)

| # | Feature | 다루는 요구사항 | 예상 규모 | 비고 |
|---|---|---|---|---|
| 10 | `artist-tier-release` | B-4 (후원자/단골 우선 공개) | M (4~5일) | 기존 sponsorship + follower 모델 활용. Post.early_access_until + 노출 필터 로직 |
| 11 | `auction-promotion-suite` | B-4 (옥션 종료 알림/홍보) | M (4~5일) | 종료 N시간 전 푸시/이메일, 공유 카드 자동 생성, 카운트다운 위젯 |

### Phase 4.5 — Deferred (데이터 축적 후 진행)

| # | Feature | 다루는 요구사항 | 예상 규모 | 보류 사유 |
|---|---|---|---|---|
| 9 | `artist-pricing-assist` | B-4 (가격 책정 보조) | L (1주) | **Deferred 2026-04-29**: 거래 데이터 일정량 축적 후 진행. 데이터 부족 시 추천 정확도 낮아 효용 떨어짐 |

### 합계
- **활성 11개 PDCA + 보류 1개**, 누적 예상 6~7주 (단일 작업자 기준, 병렬 가능 항목 있음)
- 2026-04-29 추가: #12 `notifications-ux-audit` (Phase 3 시스템 차원 작업)

---

## 3. 의존성 & 실행 순서

```
Phase 1 (병렬 가능)
  ├─ #1 role-gating ──────────────────────┐
  ├─ #2 draft-autosave ──────────────────┤
  └─ #3 responsive-redesign ─────────────┤
                                          │
Phase 2 (#3 이후 시작 권장)                │
  ├─ #4 media-ux ────┐                    │
  ├─ #5 rich-content ┤  (병렬)            │
  ├─ #7 product-meta ┘                    │
  │                                        │
  └─ #6 media-studio  (#4 완료 후 — 미디어 관리 인프라 공유)
                                          │
Phase 3 (Phase 1 완료 후)                  │
  ├─ #8 publish-controls ─────────────────┤
  └─ #12 notifications-ux-audit ──────────┤  (#8과 독립 — 병렬 가능)
                                          │
Phase 4 (Phase 3 완료 후 — 발행 옵션 위에서 동작)
  ├─ #10 tier-release   (#8의 visibility 시스템 위)
  └─ #11 auction-promo

Phase 4.5 (deferred — 데이터 축적 후)
  └─ #9 pricing-assist
```

**Critical Path** (확정 — 사용자 결정 2026-04-29 반영):
1 → 2 → 3 → 4 → 6 → 8 → 10 (약 5~6주, 사용자 지정 sequential 시작)

**병렬화 기회**:
- Phase 1: 사용자 지정으로 sequential (1 → 2 → 3) 진행. 차후 일정 압박 시 #2/#3 병렬화 가능
- Phase 2: #4/#5/#7 병렬, #6은 #4 완료 후
- Phase 4: #10/#11은 독립 — 병렬 가능

---

## 4. 시스템 차원 영향 (DB / API / 프런트)

| Feature | DB 마이그레이션 | 신규 API | 프런트 변경 영역 |
|---|---|---|---|
| #1 role-gating | 없음 | 없음 | posts/new, type 선택 UI |
| #2 draft-autosave | `posts.status` enum 'draft' 추가 (이미 있을 가능성 검증 필요) | `GET/POST/DELETE /v1/posts/draft` | posts/new, drafts 목록 페이지 |
| #3 responsive | 없음 | 없음 | posts/new 전체 재구성 |
| #4 media-ux | `media_assets.caption` text 컬럼 | `PATCH /v1/media/{id}` | post-editor/* 미디어 관련 전부 |
| #5 rich-content | 없음 (content는 그대로 markdown 저장) | 없음 (서버 렌더링 시 sanitize) | RichTextEditor 신규, FeedItem 렌더 변경 |
| #6 media-studio | `media_assets.thumbnail_url`, `media_assets.crop_meta` (옵션) | `POST /v1/media/{id}/transform` | MakingVideoModal, ImageEditor, VideoEditor 신규 |
| #7 product-meta | `products.dimensions_w/h/d`, `products.medium_enum`, `products.collaborators[]` | `GET /v1/users/search?q=` (협업자 검색) | ProductMetaForm 신규 |
| #8 publish-controls | `posts.visibility` enum, `posts.comments_enabled` bool, `series` 신규 모델 | `GET/POST /v1/series`, `POST /v1/posts/{id}/publish` | PublishOptionsPanel, 피드 노출 필터 |
| #12 notifications-ux-audit | 없음 (UI 작업 위주) — 필요 시 `notifications.deep_links` json 컬럼 검토 | 알림 클릭 핸들러 정도 | Sidebar 사용자 카드 N뱃지, UserMenu 알림 항목, NotificationCard 다중 링크, 읽음 시각화 |
| #9 pricing-assist | 없음 (분석은 기존 데이터로) | `GET /v1/artist/pricing-suggestion?genre=&medium=` | PricingGuideCard |
| #10 tier-release | `posts.early_access_until`, `posts.early_access_tier` | 노출 필터 로직 변경 | TierReleasePicker, FeedItem 잠금 표시 |
| #11 auction-promo | `auctions.notification_jobs` (또는 별도 jobs 테이블) | `POST /v1/auctions/{id}/share-card`, 알림 스케줄러 | AuctionShareCard, 알림 시스템 |

---

## 5. 산출물 (각 Sub-PDCA 별)

각 sub-feature 별로 다음을 생성한다 (PDCA 표준):

```
v1/docs/01-plan/features/{feature}.plan.md          # 본격 plan (요구사항 → 솔루션)
v1/docs/02-design/features/{feature}.design.md      # 데이터 모델 / API / UI 스펙
v1/docs/03-analysis/{feature}.analysis.md           # gap-detector 결과
v1/docs/04-report/features/{feature}.report.md      # 완료 보고서
```

본 로드맵 문서는 인덱스 역할만 하고, 실제 구현은 각 sub-PDCA에서 진행한다.

---

## 6. 본 로드맵 채택 후 다음 액션

1. **사용자 합의 항목** (이 로드맵 검토 후 답변):
   - 11개 그룹화가 적절한가? 더 잘게 쪼갤 / 합칠 항목이 있는가?
   - Phase 1의 3개 중 무엇부터 시작할지? (권장: `editor-role-gating` — 가장 작고 명확)
   - Phase 4의 가격 가이드(#9)는 데이터 축적이 필요 — 출시 직후엔 효용 낮을 수 있음. 우선순위 미루기?

2. **합의 후 진행**:
   - `/pdca plan {feature}` 명령으로 첫 sub-PDCA 진입
   - 각 sub-PDCA는 plan → design → do → check → act → report → archive 표준 사이클

---

## 7. 본 로드맵의 한계

- **시간 추정은 단일 작업자 기준** — Agent Teams 활용 시 대폭 단축 가능
- **#6 media-studio가 가장 위험** — 클라이언트 사이드(ffmpeg.wasm) vs 서버 사이드 처리 결정 시점 별도 brainstorming 필요할 수 있음
- **#9 pricing-assist는 데이터 의존** — 거래 데이터가 일정량 쌓이기 전에는 추천 정확도 낮음. MVP는 단순 통계 + 동급 작가 평균값 정도로 시작
- **백엔드 영향 큰 항목** (#2, #6, #7, #8, #10, #11)은 frontend-only 변경보다 검증 비용 큼 — gap-detector 활용 권장

---

## 8. 추적 메모

- **요구사항 출처**: 사용자 직접 입력 (2026-04-29 conversation)
- **로드맵 작성**: Claude Opus 4.7 + bkit pdca skill
- **수정 이력**: 본 문서 § 헤더의 frontmatter `date` 갱신 + 변경 부분 명시

---

## 9. 결정 기록 (Decisions Log)

### 2026-04-29 — 로드맵 채택 + 실행 전략 확정 (사용자)

| 결정 | 내용 | 근거 |
|---|---|---|
| **D-1 그룹화** | 11개 sub-PDCA 그대로 유지 | 추가 분할/통합 불요 |
| **D-2 시작 순서** | Phase 1 sequential: #1 → #2 → #3 | 권장안 채택. 위험 점진 증가 순. role-gating 부터 효과 즉시 |
| **D-3 #9 보류** | `artist-pricing-assist` 를 Phase 4.5 (별도 단계)로 분리 | 데이터 축적 부족 단계에서 추천 정확도 낮음 |
| **D-4 Agent Teams 활용** | 각 sub-PDCA에서 specialized bkit agents 활용 | `cto-lead`, `product-manager`, `frontend-architect`, `bkend-expert`, `gap-detector`, `pdca-iterator` 등 |
| **D-5 #12 추가** (2026-04-29) | `notifications-ux-audit` 12번째 sub-PDCA로 추가, Phase 3 배치 | 사용자 우려: 사용자 아이콘 N뱃지, 사용자 메뉴 알림 항목 — 알림 시스템 UX 일관성 작업 |

### Agent Teams 활용 원칙

| PDCA Phase | 담당 에이전트 (제안) |
|---|---|
| Plan (요구사항/스펙) | `bkit:product-manager` |
| Design (구조/스키마) | `bkit:frontend-architect` (UI), `bkit:bkend-expert` (DB/API) |
| Do (구현) | 메인 thread 직접 (또는 frontend-architect/bkend-expert 위임) |
| Check (gap analysis) | `bkit:gap-detector` |
| Act (auto-iterate) | `bkit:pdca-iterator` |
| Report (완료 보고) | `bkit:report-generator` |
| 대규모 PDCA (#3, #6, #8) | `bkit:cto-lead` 오케스트레이션 — 다중 agent 동원 |
