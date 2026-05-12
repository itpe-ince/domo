---
template: design
version: 1.1
feature: artist-tier-release
sub-pdca: "#10"
phase: Phase 4 — Artist Tools
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7 통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션)
project: domo
project_version: v1
parent_plan: artist-tier-release.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: M (4~5일)
status: draft
---

# artist-tier-release 설계 문서

> **요약**: B-4 후원자/단골 우선 공개. `Post.early_access_until` + `early_access_tier` 2 컬럼 추가 (alembic 0041) + `_viewer_meets_tier` 단일 UNION ALL EXISTS helper + `tier_release_jobs.py` 60s cron. **Option β 채택**: `Post.visibility` enum 미확장, `tier_only`는 계산된 effective state — R-1 완전 해소. publish endpoint 확장 (early_access_duration + early_access_tier 2 필드, 서버 산출 timestamp). Frontend `TierReleasePicker` (PublishOptionsPanel 5번째 expand) + `TierBadge` (PostCard 인디케이터) + 5 통합 지점 회귀 0.

---

## 0. OQ Resolution Echo (Plan v1.0)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | 3-tier `subscriber/sponsor/follower` | DB enum, 자격 쿼리 OR 체인 |
| OQ-2 = A | 자동 계층 포함 (subscriber > sponsor > follower) | UNION ALL EXISTS 동적 분기 |
| OQ-3 = A | 5 preset 기간 (1/6/24/72/168 hours) | Pydantic Literal + UI button group |
| OQ-4 = B | 매 조회 시 실시간 DB 검증 | 자동 만료/탈퇴 즉시 반영 |
| OQ-5 = A | 60s cron (schedule_jobs 패턴) | tier_release_jobs.py 신규 |
| OQ-6 = A | tier_only 상호 배타적 (effective 우선) | computed state |
| OQ-7 = B | 만료 후 작가 지정 visibility 복귀 | DB에 원래 visibility 보존 |
| OQ-8 = A | TierReleasePicker = PublishOptionsPanel expand | #8 패턴 일관 |
| OQ-9 = A | publish endpoint 확장 (+2 필드) | 단일 발행 흐름 |
| OQ-10 = A | no-cache (매 DB 검사) | 단순성 우선 |

10/10 모두 권장 default 채택 (사용자 결정 2026-05-03).

---

## 1. Goals & Non-Goals

### 1.1 Goals
1. 작가가 발행 시 본인의 구독자/후원자/팔로워 중 하나에게 N시간 동안 먼저 공개
2. 자동 만료 후 작가 지정 visibility(`public`/`followers_only`/`unlisted`)로 복귀
3. tier 자격 검증 = 매 조회 실시간 (구독 취소/탈퇴 즉시 반영)
4. 5 통합 지점 회귀 0
5. 외부 라이브러리 추가 0 (#8 인프라 재사용)
6. **Option β: `Post.visibility` enum 미확장 → R-1 해소**

### 1.2 Non-Goals
- pricing-assist (#9 deferred), auction-promotion-suite (#11)
- tier 자동 추천 / dynamic pricing
- tier 진입 알림 ("지금 후원하면 X시간 일찍" 등 침입적 UX)
- 후원/구독 CTA UI (POST_TIER_RESTRICTED 시 단순 메시지만)
- 만료 카운트다운 / 작가 대시보드 hint

---

## 2. Architecture Overview

### 2.1 데이터 흐름

```
[발행 버튼 클릭]
   ↓ handleSubmit() in page.tsx
[publishPost(postId, { ..., early_access_duration, early_access_tier })]
   ↓ POST /v1/posts/{id}/publish
[Backend: 서버 산출]
   ├─ early_access_until = now() + timedelta(hours=duration)
   ├─ early_access_tier = body value
   └─ post.visibility = body.visibility (작가 지정 — 만료 후 복귀)
   ↓
[조회 시 effective visibility 계산]
   ├─ if early_access_until > now() AND tier ≠ null → 'tier_only' (계산값)
   │     → _viewer_meets_tier(viewer, author, tier) 검증
   │     → 자격 있으면 200, 없으면 403 POST_TIER_RESTRICTED
   └─ else → Post.visibility 기존 로직
   ↓
[cron worker (60s)]
   └─ early_access_until <= now() AND not null → set both NULL (DB 정리)
```

### 2.2 마이그레이션 체인

```
0040_series_tables (#8)
  ↓
0041_post_tier_release (#10 — 22 chars ≤32 ✓)
   ├─ posts.early_access_until TIMESTAMP WITH TIME ZONE NULL
   ├─ posts.early_access_tier VARCHAR(20) NULL
   ├─ CHECK ck_posts_early_access_tier_enum (subscriber|sponsor|follower)
   ├─ CHECK ck_posts_early_access_pair (NULL pair consistency)
   └─ partial INDEX ix_posts_early_access_until WHERE NOT NULL
```

`Post.visibility` enum **미확장** (Option β).

---

## 백엔드 설계 (B 섹션)

> 출처: `bkit:bkend-expert` agent

### B-1. Backend 변경 개요

본 PDCA 백엔드 작업 범위는 네 묶음이다. 첫째, alembic 마이그레이션 `0041_post_tier_release.py`로 `posts` 테이블에 `early_access_until` (TIMESTAMP WITH TIME ZONE NULL) + `early_access_tier` (VARCHAR(20) NULL) 두 컬럼과 tier 값 CHECK constraint, 일관성 CHECK constraint, partial index를 추가한다. 둘째, `app/models/post.py`에 두 컬럼의 SQLAlchemy 매핑을 추가하고 `app/schemas/series.py`의 `PostPublishRequest`에 `early_access_duration` / `early_access_tier` 두 필드와 cross-field validator를 추가한다. 셋째, `app/api/posts.py`에 `_viewer_meets_tier` helper를 신규 추가하고 `_visibility_filter_for_viewer`에 effective tier_only 분기를 추가하며, `publish_post` endpoint에서 `early_access_until` 서버 산출 로직을 통합한다. 넷째, `app/services/tier_release_jobs.py` cron worker를 신규 작성하여 `app/main.py` startup에 60초 주기로 등록한다. **`Post.visibility` 컬럼 enum은 DB 레벨에서 확장하지 않는다 (Option β: §B-6) — `tier_only`는 계산된 상태이며 DB에 저장되지 않는다.**

### B-2. 데이터 모델 — `Post.early_access_until` + `Post.early_access_tier`

```python
# app/models/post.py — Post 클래스 내부, comments_enabled 아래
early_access_until: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True, default=None,
    comment="Phase 4 #10. UTC. NULL=early_access off.",
)
early_access_tier: Mapped[str | None] = mapped_column(
    String(20), nullable=True, default=None,
    comment="Phase 4 #10. 'subscriber'|'sponsor'|'follower'. NULL=off.",
)
```

NULL 의미론: 두 컬럼 모두 null = 비활성. `early_access_until <= now()` 또는 null이면 effective visibility = `Post.visibility`. `early_access_until > now()` AND `early_access_tier` set이면 effective visibility = `tier_only` (계산값).

### B-3. Alembic Migration `0041_post_tier_release.py`

revision id `0041_post_tier_release` (22 chars ✓). down_revision `0040_series_tables`.

```python
def upgrade() -> None:
    # 1. 컬럼 추가 (additive)
    op.add_column("posts", sa.Column("early_access_until",
        sa.DateTime(timezone=True), nullable=True))
    op.add_column("posts", sa.Column("early_access_tier",
        sa.String(20), nullable=True))

    # 2. tier enum CHECK
    op.create_check_constraint("ck_posts_early_access_tier_enum", "posts",
        "early_access_tier IS NULL OR "
        "early_access_tier IN ('subscriber', 'sponsor', 'follower')")

    # 3. null pair consistency CHECK
    op.create_check_constraint("ck_posts_early_access_pair", "posts",
        "(early_access_until IS NULL) = (early_access_tier IS NULL)")

    # 4. Partial index — cron worker + 자격 검증 lookup
    op.create_index("ix_posts_early_access_until", "posts",
        ["early_access_until"],
        postgresql_where=sa.text("early_access_until IS NOT NULL"))

def downgrade() -> None:
    op.drop_index("ix_posts_early_access_until", table_name="posts",
        postgresql_where=sa.text("early_access_until IS NOT NULL"))
    op.drop_constraint("ck_posts_early_access_pair", "posts", type_="check")
    op.drop_constraint("ck_posts_early_access_tier_enum", "posts", type_="check")
    op.drop_column("posts", "early_access_tier")
    op.drop_column("posts", "early_access_until")
```

> **PostgreSQL `NOW()` IMMUTABLE 제약**: WHERE 절에 NOW() 사용 불가 → `WHERE early_access_until IS NOT NULL` partial index로 대체. 활성 행만 인덱스 스캔 범위.

### B-4. Pydantic Schema

`app/schemas/series.py`에 추가:

```python
EarlyAccessTier = Literal["subscriber", "sponsor", "follower"]
EARLY_ACCESS_DURATIONS: frozenset[int] = frozenset({1, 6, 24, 72, 168})


class PostPublishRequest(BaseModel):
    publish_at: datetime | None = Field(None)
    visibility: Visibility = "public"
    comments_enabled: bool = True
    series_ids: list[uuid.UUID] = Field(default_factory=list)
    # Phase 4 #10
    early_access_duration: int | None = Field(None,
        description="우선 공개 기간(시간). 허용값: 1|6|24|72|168. None=비활성.")
    early_access_tier: EarlyAccessTier | None = Field(None)

    @field_validator("early_access_duration", mode="before")
    @classmethod
    def _validate_duration(cls, v):
        if v is None:
            return v
        if int(v) not in EARLY_ACCESS_DURATIONS:
            raise ValueError(f"INVALID_DURATION: must be one of {sorted(EARLY_ACCESS_DURATIONS)}")
        return int(v)

    def model_post_init(self, __context) -> None:
        d = self.early_access_duration
        t = self.early_access_tier
        if (d is None) != (t is None):
            raise ValueError("TIER_FIELDS_INCONSISTENT: 둘 다 set이거나 둘 다 None")


class PostPublishResponse(BaseModel):
    id: uuid.UUID
    status: str
    visibility: Visibility
    comments_enabled: bool
    scheduled_at: datetime | None
    series_count: int
    updated_at: datetime
    # Phase 4 #10
    early_access_until: datetime | None = None
    early_access_tier: str | None = None
```

`PostOut` (app/schemas/post.py)에도 3 필드 추가: `early_access_until`, `early_access_tier`, `is_tier_locked: bool = False` (viewer 기준 계산값).

### B-5. `_viewer_meets_tier` helper

`app/api/posts.py`에 신규 추가. 단일 UNION ALL EXISTS로 N+1 방지 (R-2 완화).

```python
async def _viewer_meets_tier(
    db: AsyncSession,
    viewer_id: uuid.UUID | None,
    author_id: uuid.UUID,
    required_tier: str,  # 'subscriber' | 'sponsor' | 'follower'
) -> bool:
    """OQ-2=A: 자동 계층 포함."""
    if viewer_id is None:
        return False
    if viewer_id == author_id:
        return True  # 작가 본인

    sub_q = (select(sa.literal(1))
        .where(Subscription.sponsor_id == viewer_id,
               Subscription.artist_id == author_id,
               Subscription.status == "active")
        .limit(1))
    spon_q = (select(sa.literal(1))
        .where(Sponsorship.sponsor_id == viewer_id,
               Sponsorship.artist_id == author_id,
               Sponsorship.status == "completed")
        .limit(1))
    follow_q = (select(sa.literal(1))
        .where(Follow.follower_id == viewer_id,
               Follow.followee_id == author_id)
        .limit(1))

    if required_tier == "subscriber":
        union_q = sub_q
    elif required_tier == "sponsor":
        union_q = sa.union_all(sub_q, spon_q)
    else:  # 'follower' — 가장 넓음
        union_q = sa.union_all(sub_q, spon_q, follow_q)

    exists_q = select(sa.exists(union_q))
    result = await db.execute(exists_q)
    return bool(result.scalar())
```

**자격 기준**:
- `subscriber`: `Subscription.status='active'` (취소/연체 시 즉시 상실)
- `sponsor`: `Sponsorship.status='completed'` (모든 completed 후원 인정)
- `follower`: `Follow` 행 존재

### B-6. Visibility Filter 확장 — **Option β 채택 (R-1 해소)**

**Plan v1.0 §2.1B 주석 ("계산된 effective visibility, DB 저장은 원래 visibility 유지")을 본 설계에서 공식 채택.** `Post.visibility` 컬럼은 작가 지정 값(`public`/`followers_only`/`unlisted`)을 영구 보존. `tier_only`는 DB에 저장되지 않는 **계산된 effective 상태**.

**Effective visibility**:
```
if post.early_access_until IS NOT NULL AND post.early_access_until > NOW():
    effective = 'tier_only'  (active early_access)
else:
    effective = post.visibility
```

**이점**:
- `Post.visibility` CHECK constraint 확장 불필요 → **R-1 완전 해소**
- `original_visibility` 별도 컬럼 불필요 → alembic 0041 범위 축소
- cron worker는 `early_access_until = NULL`만 처리 (visibility 컬럼 무수정)
- 만료 후 자동 복귀가 worker 지연(최대 60초)과 무관하게 실시간 처리

**`_visibility_filter_for_viewer` 확장 — 2단계 전략**:

Step 1 — SQL fast-path (active tier_only 명시 처리):
```python
now_expr = func.now()
is_active_tier = and_(
    Post.early_access_until.is_not(None),
    Post.early_access_until > now_expr,
)
is_not_active_tier = or_(
    Post.early_access_until.is_(None),
    Post.early_access_until <= now_expr,
)

# viewer=None: public + not active tier_only
# viewer 인증: 기존 로직 + active tier_only는 followee author에 한해 SQL 통과 → Python 재검증
```

Step 2 — Python post-filter (active tier_only 포스트 viewer별 자격 검증):
```python
filtered = []
for p in posts:
    if (p.early_access_until and p.early_access_until > datetime.now(timezone.utc)
        and p.early_access_tier is not None):
        qualifies = await _viewer_meets_tier(db, viewer.id, p.author_id, p.early_access_tier)
        if not qualifies:
            continue
    filtered.append(p)
posts = filtered
```

**트레이드오프**: SQL에서 tier 자격을 완전히 처리하려면 포스트마다 다른 EXISTS 서브쿼리 동적 구성 필요. active tier_only 포스트는 초기에 소수일 것이므로 Python 후처리 비용 무시할 수준. 향후 성능 측정 후 필요 시 #10.1에서 SQL subquery로 전환.

### B-7. `publish_post` endpoint 확장 (OQ-9=A)

`app/api/posts.py:publish_post()` 확장 — `comments_enabled` 처리 직후:

```python
# Phase 4 #10 OQ-9=A: tier release 통합
if body.early_access_duration is not None:
    post.early_access_until = (datetime.now(timezone.utc)
        + timedelta(hours=body.early_access_duration))
    post.early_access_tier = body.early_access_tier
else:
    post.early_access_until = None
    post.early_access_tier = None
```

**서버 산출** (클라이언트 시각 스큐 방지). audit log `extra` dict에 추가: `early_access_duration`, `early_access_tier`, `early_access_until` (ISO format). `PostPublishResponse` 반환에 2 필드 포함.

### B-8. `tier_release_jobs.py` cron worker

`app/services/tier_release_jobs.py` 신규 — `schedule_jobs.py` 패턴 미러:

```python
async def clear_expired_tier_release_once(db) -> int:
    """만료된 early_access 행 초기화 — 단일 bulk UPDATE."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(Post)
        .where(Post.early_access_until.is_not(None),
               Post.early_access_until <= now)
        .values(early_access_until=None, early_access_tier=None)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return result.rowcount


async def tier_release_cron_loop(interval_seconds: int = 60) -> None:
    """OQ-5=A: 60s loop, schedule_jobs 패턴 동일."""
    log.info("tier_release_cron_loop started (interval=%ss)", interval_seconds)
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await clear_expired_tier_release_once(db)
                if count:
                    log.info("tier_release: cleared %d post(s)", count)
        except Exception:
            log.exception("tier_release cron sweep failed")
        await asyncio.sleep(interval_seconds)
```

`app/main.py` startup에 `tier_release_task = asyncio.create_task(tier_release_cron_loop())` + lifespan finally의 `all_tasks` tuple에 추가.

> **Worker는 critical path 아님**: 실시간 visibility filter가 `early_access_until > now()` 조건으로 만료 즉시 처리. Worker는 DB 정리 역할 (인덱스 효율 유지).

### B-9. Visibility Filter 적용 — 5 endpoints

| Endpoint | 처리 |
|----------|------|
| `home_feed` (trending) | `Post.visibility == 'public' AND (early_access_until IS NULL OR early_access_until <= NOW())` |
| `home_feed` (following) | SQL filter 확장 + Python post-filter (active tier_only viewer별 재검증) |
| `explore_posts` / `search_posts` | 동일 — active tier_only 완전 제외 |
| `get_post` (단건) | 명시 분기: active tier_only → `_viewer_meets_tier()` → 비자격 시 403 POST_TIER_RESTRICTED |

`get_post` 코드 (followers_only 체크 직후):
```python
ea_until = getattr(post, "early_access_until", None)
ea_tier = getattr(post, "early_access_tier", None)
is_tier_locked = False

if ea_until and ea_until > datetime.now(timezone.utc) and ea_tier:
    is_owner = viewer_id == post.author_id
    is_admin = viewer_role == "admin"
    if not (is_owner or is_admin):
        qualifies = await _viewer_meets_tier(db, viewer_id, post.author_id, ea_tier)
        if not qualifies:
            raise ApiError("POST_TIER_RESTRICTED",
                "이 포스트는 우선 공개 기간 중입니다.", http_status=403)
    is_tier_locked = not (is_owner or is_admin)
```

`PostOut.is_tier_locked = is_tier_locked` (단건 응답에서만 채움).

### B-10. Comment Lock — 영향 0

`comments_enabled` 처리 #8과 동일. tier release는 visibility만 영향, comment endpoint 변경 0.

### B-11. Error Codes

| Code | HTTP | 발생 |
|------|:---:|------|
| `POST_TIER_RESTRICTED` | 403 | viewer가 active tier_only 자격 없음 (`GET /posts/{id}`) |
| `INVALID_TIER` | 422 | early_access_tier enum 외 |
| `INVALID_DURATION` | 422 | early_access_duration ∉ {1,6,24,72,168} |
| `TIER_FIELDS_INCONSISTENT` | 422 | duration set + tier null (또는 반대) |
| `POST_NOT_FOUND` / `POST_NOT_OWNER` / `POST_INVALID_STATE` | | (재사용) |

### B-12. Test Strategy + Implementation Order

**단위 테스트 ~9개**: `_viewer_meets_tier` 6 (None / author / subscriber / sponsor cascade / follower / sponsor with subscription) + Pydantic 2 (TIER_FIELDS_INCONSISTENT / INVALID_DURATION) + effective visibility 1 (만료 후 fallback).

**통합 테스트 ~8개**: publish with tier (DB 확인) / publish without / 422 inconsistent / get as author / get as qualifying / get as non-qualifying (403) / time-mock expired (200 fallback) / 구독 취소 후 즉시 검증 (403).

**Smoke**: `smoke_test_tier_release.sh` 5단계 (publish → author 200 → non-qualifying 403 → DB 만료 → 200 fallback).

**Implementation Order**:
- **PR1 (1.5일)**: alembic 0041 + 모델 + Pydantic + tier_release_jobs.py + main.py 등록
- **PR2 (1.5일)**: `_viewer_meets_tier` + `_visibility_filter_for_viewer` 확장 + `publish_post` 확장 + `get_post` 확장 + 5 endpoints SQL 수정 + 17 tests + 1 smoke

### B-13. Backend Risks

| ID | 리스크 | 영향 | 완화 |
|----|--------|:---:|------|
| R-1 | visibility CHECK constraint 확장 | High → **dissolved** | **Option β 채택 — visibility enum 미확장** |
| R-2 | tier 자격 N+1 | High | 단일 UNION ALL EXISTS + Python post-filter (작은 N) |
| R-3 | cron 지연 시 만료 잔존 | Low | 실시간 visibility filter가 만료 즉시 처리 (worker 비-critical) |
| R-4 | publish endpoint breaking | High → 해소 | 신규 필드 nullable + Pydantic default None |
| R-5 | UNION ALL 쿼리 플래너 비효율 | Medium | EXISTS short-circuit. `sponsorships(sponsor_id, artist_id, status)` 인덱스 부재 시 0042 minor migration 추가 |
| R-6 | Sponsorship/Subscription 모델 변경 | None | 본 PDCA에서 read-only 사용 |

---

## 프런트엔드 설계 (F 섹션)

> 출처: `bkit:frontend-architect` agent

### F-1. Frontend 변경 개요

`PublishOptionsPanel.tsx`에 5번째 sub-control인 `TierReleasePicker` expand 섹션을 추가한다. 기존 4개 섹션은 코드 변경 없이 유지되며, `TierReleasePicker`는 기본 접힘(collapsed) 상태의 `<details>` 블록으로 발행 흐름 마찰을 0으로 유지한다. `DraftState` +2 필드, `usePostFormState` +2 setters, `handleSubmit` body +2 필드 전달. PostCard에 `VisibilityBadge` 옆 `TierBadge` 인라인 추가, `/posts/[id]/page.tsx`의 load에 `POST_TIER_RESTRICTED` 403 분기 추가. i18n 22 keys × 5 locale = 110 entries.

### F-2. 의존성 + 신규 파일

**외부 라이브러리 추가: 0**. `<details>`/`<summary>` HTML 기본 요소 활용.

**신규 1**: `components/TierBadge.tsx` (VisibilityBadge 패턴 미러)

**변경 7 + i18n 5**: api.ts / useDraftAutosave / usePostFormState / PublishOptionsPanel / PostCard / posts/new/page.tsx / posts/[id]/page.tsx + i18n × 5

### F-3. 데이터 모델 (TypeScript types)

```typescript
// lib/api.ts
export type EarlyAccessTier = "subscriber" | "sponsor" | "follower";
export type EarlyAccessDuration = 1 | 6 | 24 | 72 | 168;  // hours

export interface PostPublishRequest {
  publish_at?: string | null;
  visibility: Visibility;
  comments_enabled: boolean;
  series_ids: string[];
  early_access_duration?: EarlyAccessDuration | null;
  early_access_tier?: EarlyAccessTier | null;
}

export interface PostPublishResponse {
  id: string; status: string;
  scheduled_at?: string | null;
  early_access_until?: string | null;
  early_access_tier?: EarlyAccessTier | null;
}

export interface PostView {
  // ... 기존
  early_access_until?: string | null;
  early_access_tier?: EarlyAccessTier | null;
  is_tier_locked?: boolean;
}

// DraftState (useDraftAutosave.ts)
export type DraftState = {
  // ... 기존 23 필드
  earlyAccessDuration?: EarlyAccessDuration | null;
  earlyAccessTier?: EarlyAccessTier | null;
};
```

usePostFormState +2 useState + setters + resetFromDraft `?? null` (legacy 안전).

### F-4. TierReleasePicker (PublishOptionsPanel 5번째 섹션)

`<details>` disclosure pattern (기본 접힘). PublishOptionsPanelProps +4. 헬퍼 `durationLabel(h, t)` / `tierLabel(tier, t)`.

**4 sub-section**:
1. **Tier 선택** — 3 radio (subscriber/sponsor/follower) + amber 강조 색상
2. **Duration 선택** — 5 button group (1h/6h/24h/3d/7d) + `aria-pressed`
3. **Expiry hint** — "{duration} 후 {visibility}로 공개됩니다" (OQ-7=B)
4. **Validation + Clear**:
   - 한쪽만 set → inline `role="alert"` 에러 + 발행 버튼 disable
   - Clear button: 둘 다 null로 초기화

```tsx
<details className="...">
  <summary className="...">
    {t("post.editor.publishOptions.tierRelease.label")}
    {earlyAccessDuration && earlyAccessTier && (
      <span className="ml-2 text-primary">
        {t("post.editor.publishOptions.tierRelease.activeHint", {
          duration: durationLabel(earlyAccessDuration, t),
          tier: tierLabel(earlyAccessTier, t),
        })}
      </span>
    )}
  </summary>
  <div className="pt-4 space-y-4">
    {/* tier radio + duration button group + expiry hint + validation + clear */}
  </div>
</details>
```

### F-5. TierBadge

신규 `components/TierBadge.tsx` — VisibilityBadge 패턴:
- `early_access_until` null/만료 → `null` 반환
- `early_access_tier`별 i18n label
- amber 색상 (text-amber-600)
- LockClosedIcon (#8 도입)

PostCard 통합: VisibilityBadge wrapper div 감싸기 + TierBadge 추가.

### F-6. handleSubmit 갱신

`publishPost` body +2 필드. `mapPublishError` +3 코드 (INVALID_TIER / INVALID_DURATION / TIER_FIELDS_INCONSISTENT). 발행 버튼 `disabled` 조건에 `tierInconsistent` 추가.

`POST_TIER_RESTRICTED`는 발행 시 발생하지 않음 — `/posts/[id]` 진입 시 처리 (§F-8).

### F-7. Form State 통합 (5 통합 지점 회귀 0)

| 지점 | 변경 | 회귀 |
|------|------|:---:|
| useDraftAutosave | DraftState +2 optional | 0 |
| DraftRestoreDialog | resetFromDraft `?? null` | 0 |
| 멀티탭 sync | JSON round-trip | 0 |
| role-gating | TierReleasePicker 모든 role | 0 |
| useArtistGate | zero coupling | 0 |

### F-8. /posts/[id] POST_TIER_RESTRICTED 처리

`load()` catch에 분기 추가:
```typescript
if (e instanceof ApiClientError && e.code === "POST_TIER_RESTRICTED") {
  setError(t("post.detail.tierRestricted"));
}
```

후원/구독 CTA UI는 본 PDCA 범위 밖 (§F-12).

### F-9. i18n 신규 키 (~22 keys × 5 locales = 110 entries)

**`post.editor.publishOptions.tierRelease.*` (15 keys)**:
- `label`, `activeHint`, `tier.{label,subscriber,sponsor,follower}`, `duration.{label,1h,6h,24h,3d,7d}`, `expiryHint`, `clear`, `errorBothRequired`

**`post.feed.indicator.tier.*` (3 keys)**: `subscriber`/`sponsor`/`follower`

**`post.editor.error.*` 신규 (3 keys)**: `invalidTier`/`invalidDuration`/`tierFieldsInconsistent`

**`post.detail.*` 신규 (1 key)**: `tierRestricted`

**총 22 keys × 5 = 110 entries**. 한국어 reference 위 §F-9 표 참조 (en/ja/zh-Traditional/es 모두 표에 명세).

### F-10. Implementation Order PR3 (~1.5일)

11 step: types → DraftState → form state → PublishOptionsPanel → TierBadge → PostCard → page.tsx → posts/[id] → i18n → tsc → 5 통합 지점 회귀 검증

### F-11. Frontend Risks

| ID | 리스크 | 영향 | 완화 |
|----|--------|:---:|------|
| R-FE-1 | `<details>` summary marker 브라우저 차이 | Low | `[&::marker]:hidden` Tailwind 또는 `list-style: none` |
| R-FE-2 | tier/duration 한쪽 set 발행 방지 누락 | Medium | `tierInconsistent` boolean — 발행 버튼 + Pydantic 두 layer 방어 |
| R-FE-3 | TierBadge + VisibilityBadge overflow | Low | wrapper `flex items-center gap-1` (~60px 합산) |
| R-FE-4 | 클라이언트 시계와 서버 UTC 만료 판정 오차 | Low | TierBadge expired 판정은 표시용. 실제 접근 제어는 서버. ±몇 분 허용 |
| R-FE-5 | `t()` named placeholder 지원 | Medium | #8 `.replace("{tz}", tz)` 패턴 그대로 적용 |
| R-FE-6 | DraftPayload 타입 누락 시 tsc | Low | Step 1에서 lib/api.ts 먼저 확장 |

### F-12. 향후 Enhancement (out of scope)

- 후원/구독 CTA UI / 카운트다운 / 작가 대시보드 hint / viewer 자격 강조 / Disclosure 라이브러리 교체

---

## 11. New Open Questions for Design Phase (OQ-D) — ✅ ALL RESOLVED (v1.1, 2026-05-03)

| ID | 영역 | 결정 | 영향 |
|----|------|------|------|
| **OQ-D-1 = B** | Backend | **Option β** — `Post.visibility` enum 미확장, `tier_only`는 계산된 effective state | R-1 완전 해소, alembic 0041은 신규 컬럼만 |
| **OQ-D-2 = B** | Frontend | 22 keys (duration sub-keys 5개 분리) | 5 locale × 22 = 110 entries |
| **OQ-D-3 = B** | Backend | SQL fast-path + Python post-filter (2단계) | active tier_only 소수 N에 적합, #10.1에서 SQL 전환 가능 |
| **OQ-D-4 = A** | Backend | `sponsor` 자격 = 모든 completed Sponsorship 인정 | Plan §2.1A 기준, N일 제한은 #10.1 carry-over |
| **OQ-D-5 = A** | Backend | `sponsorships(sponsor_id, artist_id, status)` 복합 인덱스를 alembic 0041에 통합 | R-5 즉시 완화 |

> 5/5 모두 권장 default 채택 (사용자 결정 2026-05-03). **Design v1.1 → /pdca do 진입 가능.**

---

## 12. Test Strategy 통합

| 영역 | 검증 |
|------|------|
| Backend 단위 | 9개 (`_viewer_meets_tier` 6 + Pydantic 2 + effective visibility 1) |
| Backend 통합 | 8개 (publish 3 + get_post 4 + 구독 취소 실시간 1) |
| Backend Smoke | `smoke_test_tier_release.sh` 5단계 |
| Frontend 5 통합 지점 | PR3 마지막 단계 검증 |
| Frontend Viewport | 375 / 768 / 1024 / 1280 |
| Frontend 5 locale | ko/en/ja/zh-Traditional/es (~22 keys × 5 = 110 entries) |
| End-to-end | publish with tier → 작가 본인 200 + 자격 viewer 200 + 비자격 viewer 403 → 1시간 후 fallback to public |

---

## 13. Implementation Order 통합

| Step | 영역 | 작업 | 기간 |
|------|------|------|:---:|
| 1 | Backend | alembic 0041 + Post 모델 +2 필드 + Pydantic schema 확장 + tier_release_jobs.py + main.py 등록 | 1.5일 |
| 2 | Backend | `_viewer_meets_tier` + `_visibility_filter_for_viewer` 확장 + `publish_post` 확장 + `get_post` 확장 + 5 endpoints SQL 수정 + 17 tests + smoke | 1.5일 |
| 3 | Frontend | api.ts types + DraftState + usePostFormState + PublishOptionsPanel TierReleasePicker + TierBadge + PostCard + handleSubmit + posts/[id] 403 분기 + i18n 22 keys × 5 + tsc + 5 통합 지점 회귀 | 1.5일 |

총 **4.5일** (Backend 3 + Frontend 1.5). Step 1 일부 (api.ts types)와 Step 3 시작 병렬 가능 → 단축 4일.

---

## 14. Risks Summary

핵심 위험: **R-1 (해소됨), R-2 N+1, R-5 인덱스**.

| 영역 | 핵심 위험 | 완화 |
|------|-----------|------|
| Backend | R-1 visibility CHECK 확장 | **Option β로 완전 해소 — alembic 0041은 신규 컬럼만** |
| Backend | R-2 tier 자격 N+1 | UNION ALL EXISTS + 2단계 SQL+Python 전략 |
| Backend | R-5 `sponsorships` 인덱스 | OQ-D-5=A 채택 시 0041 통합 |
| Backend | R-3 cron 지연 | 실시간 filter가 critical path — worker 비-critical |
| Frontend | R-FE-2 tier/duration 일관성 | 발행 버튼 + Pydantic 2 layer |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-03 | Initial draft. bkit:bkend-expert (B-1~B-13) + bkit:frontend-architect (F-1~F-12) 병렬 위임 → 통합. 10 OQ resolved (Plan v1.0) + 5 OQ-D surface. **OQ-D-1=B (Option β) 핵심 결정 — Post.visibility enum 미확장, tier_only는 계산값**. alembic 0041 + 2 컬럼 + UNION ALL EXISTS helper + 60s cron + TierReleasePicker (PublishOptionsPanel 5번째 expand) + TierBadge + 5 통합 지점 회귀 0 명세. | itpe-ince + Claude Opus 4.7 (통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션) |
| 1.1 | 2026-05-03 | OQ-D 5/5 모두 권장 default 일괄 수락 (사용자 결정). §11 OQ-D 표를 결정 echo로 변환. OQ-D-5=A 채택으로 alembic 0041에 `ix_sponsorships_sponsor_artist_status` 복합 인덱스 통합. /pdca do 진입 가능. | itpe-ince |
