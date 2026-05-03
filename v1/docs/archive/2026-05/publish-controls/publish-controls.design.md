---
template: design
version: 1.1
feature: publish-controls
sub-pdca: "#8"
phase: Phase 3 — Publishing System
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7 통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션)
project: domo
project_version: v1
parent_plan: publish-controls.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
estimate: L (1.5주, 11일)
status: draft
---

# publish-controls 설계 문서

> **요약**: B-3 발행 옵션 4건(공개범위/댓글허용/시리즈/예약발행)을 통합한 `POST /v1/posts/{id}/publish` 단일 엔드포인트 + 신규 Series 모델 + `PublishOptionsPanel` UI. alembic 0039 (visibility + comments_enabled + 복합 인덱스) + 0040 (series + post_series_membership). dnd-kit 재사용 (외부 lib 추가 0). 5 통합 지점 회귀 0.

---

## 0. OQ Resolution Echo (Plan v1.0)

| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = A | enum `public/followers_only/unlisted` | DB column type, API filter, UI labels |
| OQ-2 = A | 기존 행 모두 `public` backfill | alembic 0039 default value |
| OQ-3 = A | comments_enabled=false 시 기존 댓글 보존 (읽기 전용) | API: 신규 POST /comments만 차단 |
| OQ-4 = C | cover_url 수동 우선 + 첫 포스트 thumbnail fallback | DB nullable + 프런트 fallback |
| OQ-5 = A | 시리즈 내 포스트 drag-reorder | `#4 dnd-kit` 재사용 |
| OQ-6 = A | scheduled_at 5분~1년 범위 | Pydantic validator |
| OQ-7 = A | unlisted 포스트 URL `/posts/{uuid}` 그대로 | 추가 라우팅 0 |
| OQ-8 = A | PublishOptionsPanel = wizard step + 사이드바 | `#3 + #4` 패턴 재사용 |
| OQ-9 = A | `POST /v1/posts/{id}/publish` 신규 endpoint | semantic clarity, audit log |
| OQ-10 = A | SQLAlchemy WHERE + 복합 인덱스 `posts(visibility, status, created_at DESC)` | alembic 0039에 인덱스 함께 |

> 10/10 모두 권장 default 채택 (사용자 결정 2026-05-03).

---

## 1. Goals & Non-Goals

### 1.1 Goals
1. 작가가 발행 시점에 (a) 공개 범위, (b) 댓글 허용, (c) 시리즈 묶기, (d) 예약 발행을 통합 제어
2. visibility 시스템을 Phase 4 #10 `artist-tier-release`의 기반으로 제공 (`String(20)` enum 확장 여유)
3. Series 신규 모델 + M:N membership으로 작가의 작품 갤러리 큐레이션 지원
4. 5 통합 지점 회귀 0 (autosave/DraftRestoreDialog/multi-tab/role-gating/useArtistGate)
5. 외부 라이브러리 추가 0 (dnd-kit는 #4에서 도입됨)

### 1.2 Non-Goals
- Tier-based 공개 (sponsor-only) — Phase 4 #10
- Comment moderation (신고/숨김) — 별도 기능
- 시리즈 결제/구독 — Phase 4.5
- 외부 SNS 공유 자동화 — 별도 PDCA

---

## 2. Architecture Overview

### 2.1 데이터 흐름

```
[발행 버튼 클릭]
   ↓ handleSubmit() in page.tsx
[publishPost(postId, { publish_at, visibility, comments_enabled, series_ids })]
   ↓ POST /v1/posts/{id}/publish
[Backend 6단계 권한 검증 → 트랜잭션]
   ├─ status 전이: draft → 'scheduled' | 'pending_review' | 'published'
   ├─ visibility / comments_enabled 컬럼 갱신
   ├─ post_series_membership 일괄 갱신 (cross-ownership 검증)
   └─ audit log: post.publish.applied
   ↓
[PostPublishResponse]
   ↓ router.push(`/posts/{id}` 또는 scheduled redirect)
```

### 2.2 마이그레이션 체인

```
0036_media_caption (#4)
  ↓
0037_media_crop_meta (#6-image)
  ↓
0038_orig_signature_keys (#6-image)
  ↓
0039_post_visibility_comments (#8 — Post.visibility + comments_enabled + ix_posts_visibility_status_created)
  ↓
0040_series_tables (#8 — series + post_series_membership)
```

revision ID 길이 모두 ≤32 (lessons learned from #6-image v1.3).

---

## 백엔드 설계 (B 섹션)

> 출처: `bkit:bkend-expert` agent

### B-1. Backend 변경 개요

본 PDCA 백엔드 작업 범위는 크게 세 묶음이다. 첫째, alembic 마이그레이션 2개 (`0039_post_visibility_comments`, `0040_series_tables`)로 `posts` 테이블에 `visibility` / `comments_enabled` 컬럼과 복합 인덱스를 추가하고, `series` + `post_series_membership` 신규 테이블을 생성한다. 둘째, `app/models/series.py` 신규 SQLAlchemy 모델, `app/schemas/post.py` 확장, `app/schemas/series.py` 신규 Pydantic 스키마를 추가한다. 셋째, `POST /v1/posts/{id}/publish` 신규 엔드포인트, Series CRUD 라우터 (`app/api/series.py`), 그리고 `home_feed` / `explore_posts` / `search_posts` / `my_bookmarks` 등 5개 엔드포인트에 visibility WHERE 필터를 적용한다. `schedule_jobs.py`는 status 전환만 담당하므로 변경 불필요.

### B-2. 데이터 모델 — `Post.visibility` + `Post.comments_enabled`

`MediaAsset.crop_meta` 패턴 (#6-image §B-2) 그대로 적용 — `NOT NULL + DEFAULT`로 설계.

```python
# app/models/post.py — Post 클래스 내부에 추가
visibility: Mapped[str] = mapped_column(
    String(20), nullable=False, default="public",
    comment="OQ-1=A. Phase 4 #10이 'tier_only' 등 추가 가능."
)
comments_enabled: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=True,
    comment="OQ-3=A. False 시 POST /comments 차단, 기존 댓글 보존."
)
```

**NULL 의미론**:
- `NOT NULL` — alembic 마이그레이션에서 backfill 후 NOT NULL 제약 추가
- `visibility` 기본 `'public'`, `comments_enabled` 기본 `True` — 기존 동작 완전 보존
- `String(20)` 여유 — Phase 4 #10이 `'tier_only'` 등 additive 확장 가능

### B-3. 데이터 모델 — `Series` + `post_series_membership`

신규 파일 `app/models/series.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Series(Base):
    __tablename__ = "series"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # OQ-4=C
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["PostSeriesMembership"]] = relationship(
        back_populates="series",
        cascade="all, delete-orphan",
        order_by="PostSeriesMembership.order_index",
    )


class PostSeriesMembership(Base):
    __tablename__ = "post_series_membership"

    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("series.id", ondelete="CASCADE"),
        primary_key=True,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    series: Mapped["Series"] = relationship(back_populates="memberships")
```

**인덱스**:
- `ix_series_author_id` — `GET /v1/series?author_id=` 쿼리
- `ix_psm_post_id` — `POST /v1/posts/{id}/series` 기존 membership 삭제 시

`app/models/__init__.py`에 `Series`, `PostSeriesMembership` import 추가 필요.

### B-4. Alembic Migration `0039_post_visibility_comments.py`

revision ID = `0039_post_visibility_comments` (30 chars, ≤32 ✓).

```python
revision: str = "0039_post_visibility_comments"
down_revision: Union[str, None] = "0038_orig_signature_keys"

def upgrade() -> None:
    # 1. visibility 컬럼 추가 (nullable → backfill → NOT NULL)
    op.add_column("posts", sa.Column("visibility", sa.String(20), nullable=True))
    op.execute("UPDATE posts SET visibility = 'public' WHERE visibility IS NULL")
    op.alter_column("posts", "visibility", nullable=False)
    op.create_check_constraint(
        "ck_posts_visibility_enum", "posts",
        "visibility IN ('public', 'followers_only', 'unlisted')",
    )

    # 2. comments_enabled
    op.add_column("posts", sa.Column("comments_enabled", sa.Boolean, nullable=True))
    op.execute("UPDATE posts SET comments_enabled = TRUE WHERE comments_enabled IS NULL")
    op.alter_column("posts", "comments_enabled", nullable=False)

    # 3. 복합 인덱스 — OQ-10=A
    op.create_index(
        "ix_posts_visibility_status_created", "posts",
        ["visibility", "status", sa.text("created_at DESC")],
    )

def downgrade() -> None:
    op.drop_index("ix_posts_visibility_status_created", table_name="posts")
    op.drop_constraint("ck_posts_visibility_enum", "posts", type_="check")
    op.drop_column("posts", "comments_enabled")
    op.drop_column("posts", "visibility")
```

### B-5. Alembic Migration `0040_series_tables.py`

revision ID = `0040_series_tables` (18 chars ✓).

```python
revision: str = "0040_series_tables"
down_revision: Union[str, None] = "0039_post_visibility_comments"

def upgrade() -> None:
    op.create_table(
        "series",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("cover_url", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_series_author_id", "series", ["author_id"])

    op.create_table(
        "post_series_membership",
        sa.Column("series_id", UUID(as_uuid=True),
                  sa.ForeignKey("series.id", ondelete="CASCADE"),
                  primary_key=True, nullable=False),
        sa.Column("post_id", UUID(as_uuid=True),
                  sa.ForeignKey("posts.id", ondelete="CASCADE"),
                  primary_key=True, nullable=False),
        sa.Column("order_index", sa.Integer, default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_psm_post_id", "post_series_membership", ["post_id"])

def downgrade() -> None:
    op.drop_index("ix_psm_post_id", table_name="post_series_membership")
    op.drop_table("post_series_membership")
    op.drop_index("ix_series_author_id", table_name="series")
    op.drop_table("series")
```

### B-6. Pydantic Schemas

신규 파일 `app/schemas/series.py`:

```python
import uuid
from datetime import datetime, timezone, timedelta
from typing import Literal
from pydantic import BaseModel, Field, field_validator


Visibility = Literal["public", "followers_only", "unlisted"]


class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_url: str | None = None


class SeriesPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover_url: str | None = None


class SeriesOut(BaseModel):
    id: uuid.UUID
    author_id: uuid.UUID
    title: str
    description: str | None
    cover_url: str | None
    created_at: datetime
    updated_at: datetime
    post_count: int = 0
    model_config = {"from_attributes": True}


class PostPublishRequest(BaseModel):
    publish_at: datetime | None = Field(
        None, description="None=즉시. 존재 시 예약 발행. UTC 권장."
    )
    visibility: Visibility = "public"
    comments_enabled: bool = True
    series_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("publish_at", mode="before")
    @classmethod
    def _validate_publish_at(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if v < now + timedelta(minutes=5):
            raise ValueError("SCHEDULED_AT_TOO_SOON")
        if v > now + timedelta(days=365):
            raise ValueError("SCHEDULED_AT_TOO_FAR")
        return v


class PostPublishResponse(BaseModel):
    id: uuid.UUID
    status: str
    visibility: Visibility
    comments_enabled: bool
    scheduled_at: datetime | None
    series_count: int
    updated_at: datetime


class PostSeriesUpdateIn(BaseModel):
    series_ids: list[uuid.UUID] = Field(...)
```

`app/schemas/post.py` `PostOut`에 두 필드 추가:
```python
visibility: str = "public"
comments_enabled: bool = True
```

### B-7. `POST /v1/posts/{id}/publish` 엔드포인트

6단계 권한 흐름 (mirror #6-image §B-5):
1. `get_current_user` → 401
2. Post not found → `POST_NOT_FOUND` 404
3. `post.author_id != user.id` → `POST_NOT_OWNER` 403
4. `post.status not in {'draft','scheduled','pending_review'}` → `POST_INVALID_STATE` 409
5. `body.visibility != post.visibility` AND active auction 존재 → `AUCTION_ACTIVE_VISIBILITY_LOCKED` 409 (FR-12, R-8 완화)
6. 트랜잭션: status 전이 + visibility/comments_enabled 갱신 + series 갱신 + audit log + commit

```python
_PUBLISHABLE_STATUSES = {"draft", "scheduled", "pending_review"}

async def _check_auction_visibility_lock(db, post):
    if not post.product:
        return
    result = await db.execute(
        select(Auction).where(
            Auction.product_post_id == post.id, Auction.status == "active"
        )
    )
    if result.scalar_one_or_none():
        raise ApiError("AUCTION_ACTIVE_VISIBILITY_LOCKED",
                       "Cannot change visibility during active auction",
                       http_status=409)

async def _replace_post_series(db, post_id, series_ids, user_id):
    """기존 membership 제거 + 각 series 소유자 검증 + 재생성. R-8 완화."""
    existing = await db.execute(
        select(PostSeriesMembership).where(PostSeriesMembership.post_id == post_id)
    )
    for m in existing.scalars().all():
        await db.delete(m)
    if not series_ids:
        return 0
    series_result = await db.execute(select(Series).where(Series.id.in_(series_ids)))
    series_map = {s.id: s for s in series_result.scalars().all()}
    for sid in series_ids:
        if sid not in series_map:
            raise ApiError("SERIES_NOT_FOUND", f"Series {sid} not found", http_status=404)
        if series_map[sid].author_id != user_id:
            raise ApiError("SERIES_NOT_OWNER",
                           f"Series {sid} does not belong to you", http_status=403)
    for idx, sid in enumerate(series_ids):
        db.add(PostSeriesMembership(series_id=sid, post_id=post_id, order_index=idx))
    return len(series_ids)


@router.post("/{post_id}/publish", status_code=200)
async def publish_post(
    post_id: UUID,
    body: PostPublishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("post_publish"),
):
    post = await _load_post_full(db, post_id)
    if not post or post.status == "deleted":
        raise ApiError("POST_NOT_FOUND", http_status=404)
    if post.author_id != user.id and user.role != "admin":
        raise ApiError("POST_NOT_OWNER", http_status=403)
    if post.status not in _PUBLISHABLE_STATUSES:
        raise ApiError("POST_INVALID_STATE",
                       f"Post status '{post.status}' cannot be published",
                       http_status=409)
    if body.visibility != getattr(post, "visibility", "public"):
        await _check_auction_visibility_lock(db, post)

    prev_status = post.status
    if body.publish_at:
        post.status = "scheduled"
        post.scheduled_at = body.publish_at
    else:
        has_visual = any(m.type in ("image", "video") for m in (post.media or []))
        post.status = "pending_review" if has_visual else "published"
        post.scheduled_at = None

    post.visibility = body.visibility
    post.comments_enabled = body.comments_enabled
    series_count = await _replace_post_series(db, post.id, body.series_ids, user.id)

    await db.flush()
    _log.info("post.publish.applied post_id=%s prev=%s new=%s vis=%s comments=%s series=%d",
              post.id, prev_status, post.status, body.visibility,
              body.comments_enabled, series_count)
    await db.commit()
    await db.refresh(post)

    return {"data": PostPublishResponse(
        id=post.id, status=post.status, visibility=post.visibility,
        comments_enabled=post.comments_enabled, scheduled_at=post.scheduled_at,
        series_count=series_count, updated_at=post.updated_at,
    ).model_dump(mode="json")}
```

### B-8. Series CRUD Endpoints

신규 파일 `app/api/series.py`. 핵심 헬퍼:

```python
async def _check_series_owner(series, user):
    """R-8 완화: 모든 series mutation에 호출 필수."""
    if series.author_id != user.id and user.role != "admin":
        raise ApiError("SERIES_NOT_OWNER", http_status=403)
```

엔드포인트:
- `GET /v1/series?author_id=` (default: 본인) — `series_read` rate limit
- `POST /v1/series` (`SeriesCreate`) → 201 `SeriesOut`
- `GET /v1/series/{id}` — 시리즈 + 소속 포스트 (order_index 순)
- `PATCH /v1/series/{id}` — owner 검증
- `DELETE /v1/series/{id}` — owner 검증, CASCADE membership만 삭제 (Post 자체 유지)
- `POST /v1/posts/{id}/series` (`PostSeriesUpdateIn`) — 포스트 소유자 + 각 series 소유자 cross-check (R-8 핵심)

### B-9. Visibility Filter — Feed/Explore/Search/Profile

공통 헬퍼 (`app/core/visibility.py` 신규 또는 `app/api/posts.py` 상단):

```python
def _visibility_filter_for_viewer(viewer, author_id_col, viewing_self, followee_ids=None):
    """피드/탐색/검색/프로필에서 viewer 권한별 visibility WHERE 절 반환."""
    if viewing_self:
        return sa.true()
    if viewer is None:
        return Post.visibility == "public"
    if followee_ids is not None:
        return or_(
            Post.visibility == "public",
            and_(Post.visibility == "followers_only",
                 author_id_col.in_(followee_ids)),
        )
    follows_subq = (
        select(Follow.followee_id).where(Follow.follower_id == viewer.id).scalar_subquery()
    )
    return or_(
        Post.visibility == "public",
        and_(Post.visibility == "followers_only", author_id_col.in_(follows_subq)),
    )
```

엔드포인트별 적용:
| 엔드포인트 | visibility 조건 |
|-----------|----------------|
| `home_feed` trending | `public` 고정 |
| `home_feed` following | `public` + `followers_only` (followee author) |
| `explore_posts` / `search_posts` | `public` 고정 |
| `my_bookmarks` | `OR(author_id==me, visibility=='public')` |
| `GET /users/{id}/posts` | `_visibility_filter_for_viewer(...)` |
| `GET /posts/{id}` 단일 | followers_only → 팔로우 검사, unlisted → URL 직접 접근 허용 (OQ-7=A) |

### B-10. Comment Lock — `comments_enabled=false`

`app/api/posts.py` `create_comment` 진입 직후:

```python
if not post.comments_enabled:
    raise ApiError("COMMENTS_DISABLED", "Comments are disabled", http_status=403)
```

기존 `GET /posts/{id}/comments` 변경 없음 (OQ-3=A 보존).

### B-11. Error Codes

| Code | HTTP | Trigger |
|------|------|---------|
| `POST_NOT_FOUND` | 404 | (재사용) |
| `POST_NOT_OWNER` | 403 | (재사용) |
| `POST_INVALID_STATE` | 409 | publish 시 status 비전이가능 |
| `POST_VISIBILITY_RESTRICTED` | 403 | followers_only 비팔로워 직접 접근 |
| `COMMENTS_DISABLED` | 403 | comment 작성 시 비허용 |
| `SCHEDULED_AT_TOO_SOON` | 422 | publish_at < now+5min |
| `SCHEDULED_AT_TOO_FAR` | 422 | publish_at > now+1y |
| `SERIES_NOT_FOUND` | 404 | series_id 미존재 |
| `SERIES_NOT_OWNER` | 403 | 타인 시리즈 mutation (R-8) |
| `AUCTION_ACTIVE_VISIBILITY_LOCKED` | 409 | active auction 포스트 visibility 변경 |
| `INVALID_VISIBILITY` | 422 | enum 외 값 (Pydantic Literal 자동) |

### B-12. Rate Limit Scopes

`app/core/rate_limit.py` `DEFAULT_LIMITS`:

```python
"post_publish": {"limit": 10, "window_sec": 60, "by": "user"},
"series_write": {"limit": 30, "window_sec": 60, "by": "user"},
"series_read":  {"limit": 60, "window_sec": 60, "by": "user"},
```

### B-13. Test Strategy + Implementation Order

**단위 테스트 ~10개**:
- `_visibility_filter_for_viewer` 4종 (None / non-follower / follower / self)
- `publish_at` validator 3종 (too soon / too far / valid)
- `comments_enabled` 차단 1
- `_check_series_owner` cross-check 1
- Series cascade 검증 1

**통합 테스트 ~12개**: publish 7 (즉시/예약/403/404/409 invalid_state/422 scheduled_at/with series) + series CRUD 5 (create/get/patch/delete/cross-ownership)

**Smoke**: `smoke_test_publish_controls.sh` (publish + visibility + comments + scheduled), `smoke_test_series.sh` (CRUD + cross-ownership)

**Backend Implementation Order**:
- **PR1 (3일)**: alembic 0039+0040 + 모델 + Pydantic + Series CRUD + visibility filter + comments lock
- **PR2 (2일)**: `POST /v1/posts/{id}/publish` + audit log + 22 tests + 2 smoke

### B-14. Backend Risks

| ID | 리스크 | 영향 | 완화 |
|----|--------|:---:|------|
| R-1 | visibility WHERE 인덱스 미적용 | High | `0039`에 `ix_posts_visibility_status_created` 필수, EXPLAIN ANALYZE 검증 |
| R-2 | followers_only N+1 | Medium | `home_feed`의 followee_ids 재사용 |
| R-3 | scheduled cron이 신규 컬럼 인식 실패 | Low | `selectinload` 자동 로드, 변경 불필요 |
| R-4 | scheduled_at TZ 불일치 | Medium | Pydantic `tzinfo=None`→UTC 강제, 5분 버퍼 흡수 |
| R-5 | CASCADE 오해 (Series 삭제 시 Post 삭제) | Low | `ondelete="CASCADE"`는 membership만, smoke로 검증 |
| R-6 | `_check_series_owner` 누락 | High | 모든 mutation에 헬퍼 호출 + smoke `OTHER_TOKEN` cross-check |
| R-7 | Phase 4 #10 enum 확장 시 CHECK 수정 | Medium | additive alembic으로 처리 가능, String(20) 여유 |

---

## 프런트엔드 설계 (F 섹션)

> 출처: `bkit:frontend-architect` agent

### F-1. Frontend 변경 개요

`PublishOptionsPanel` 신규 컴포넌트 한 개로 4개 제어를 묶는다. 외부 의존성 추가 없이 `dnd-kit`(#4에서 도입)을 `/series/[id]` 편집 모드 drag-reorder에 재사용. `usePostFormState` + `useDraftAutosave`에 신규 필드 3개 추가가 기존 JSON 직렬화 구조를 유지하므로 5 통합 지점 회귀 0. 데스크탑 우측 sidebar slot은 `PreviewPane` 아래에 sticky 섹션으로 배치 (`#3+#4` 패턴).

### F-2. 의존성 + 신규 라우팅

**외부 의존성 추가: 0** (dnd-kit는 #4에서 도입됨).

| 경로 | 파일 | 설명 |
|------|------|------|
| `/series/[id]` | `app/series/[id]/page.tsx` | 시리즈 상세 + 편집 모드 |
| `/users/[id]/series` | `app/users/[id]/series/page.tsx` | 작가 프로필 시리즈 탭 (별도 라우트, 권장) |
| `/posts/new` 확장 | wizard step `publish-options` 추가 | 기존 라우트 유지 |

> Next.js App Router에서 `searchParams`-driven tab은 Server Component 캐싱 충돌 위험이 있어 별도 라우트가 명확.

### F-3. 데이터 모델 (TypeScript types)

`lib/api.ts`에 추가:
```typescript
export type Visibility = "public" | "followers_only" | "unlisted";

export interface Series { id, author_id, title, description?, cover_url?, created_at, updated_at, post_count? }
export interface SeriesCreate { title, description?, cover_url? }
export interface SeriesPatch { title?, description?, cover_url? }
export interface SeriesWithPosts { series, posts }

export interface PostPublishRequest {
  publish_at: string | null;
  visibility: Visibility;
  comments_enabled: boolean;
  series_ids: string[];
}
export interface PostPublishResponse { id, status, visibility, publish_at }

// API client 7개:
export async function listMySeries(): Promise<Series[]>
export async function listSeriesByAuthor(authorId): Promise<Series[]>
export async function createSeries(body): Promise<Series>
export async function patchSeries(id, body): Promise<Series>
export async function deleteSeries(id): Promise<void>
export async function getSeriesWithPosts(id): Promise<SeriesWithPosts>
export async function setPostSeriesIds(postId, seriesIds): Promise<void>
export async function publishPost(postId, body): Promise<PostPublishResponse>
```

`DraftState` 확장 (legacy 호환):
```typescript
visibility?: Visibility;       // undefined → "public"
commentsEnabled?: boolean;     // undefined → true
seriesIds?: string[];          // undefined → []
```

### F-4. PublishOptionsPanel 컴포넌트

신규 `components/post-editor/PublishOptionsPanel.tsx`. 4 sub-control:

- **VisibilitySelector**: 라디오 그룹 3 옵션 (🌐 public / 🔒 followers_only / 🔗 unlisted) + 각 i18n description
- **CommentsToggle**: switch (`bg-primary` on / `bg-surface-hover` off) + hint "기존 댓글은 보존"
- **SeriesSelector**: checkbox list + post_count badge + "+ 새 시리즈 만들기" CTA
- **ScheduledPicker**: `<input type="datetime-local" />` + 5분~1년 client validation + `Intl.DateTimeFormat().resolvedOptions().timeZone` 표시 + Clear button

### F-5. SeriesCreateModal

신규 `components/post-editor/SeriesCreateModal.tsx` — `#6-image SignatureUploadModal` 패턴 미러. z-[60], focus trap, ESC, 배경 클릭 close. Fields: title (required, max 200), description (optional textarea), cover_url upload (optional, null이면 첫 포스트 thumbnail fallback). `onCreated(newSeries)` callback으로 SeriesSelector에 prepend.

### F-6. useMySeries hook

신규 `lib/hooks/useMySeries.ts` — `useSignature` 패턴 미러. GET on mount + add (optimistic prepend) + update + remove (optimistic + rollback) + refresh.

### F-7. Wizard Step Integration (모바일)

`useEditorWizardStep.ts` 갱신:
```typescript
export type WizardStep = "type" | "content" | "product_meta" | "publish-options" | "publish";
const GENERAL_STEPS = ["type", "content", "publish-options", "publish"];
const PRODUCT_STEPS = ["type", "content", "product_meta", "publish-options", "publish"];
```

`EditorMobileWizard.tsx`에 `publish-options` step 분기 추가 → `EditorStepPublishOptions` 신규 wrapper.

### F-8. EditorWorkspace 데스크탑 통합

`EditorWorkspace`/`page.tsx` — PreviewPane 아래에 `<aside>` sticky 섹션 추가:
```tsx
{isPreviewVisible && (
  <aside className="hidden md:block w-96 border-l border-border bg-background overflow-y-auto">
    <div className="p-4 space-y-1">
      <h2>{t("post.editor.publishOptions.title")}</h2>
      <PublishOptionsPanel ... />
    </div>
  </aside>
)}
```

### F-9. /series/[id] 페이지

신규 `app/series/[id]/page.tsx`:
- 헤더: cover (cover_url → 첫 포스트 thumbnail fallback → 이니셜 placeholder) + 제목 + author + post_count + (소유자) 편집 모드 토글
- 편집 모드 (소유자): `dnd-kit` `<DndContext>` + `<SortableContext>` + drag handle + remove button. **저장 버튼 클릭 시에만** API 호출 (R-FE-2)
- 갤러리: order_index 순 + `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4`

### F-10. 작가 프로필 시리즈 탭

신규 `app/users/[id]/series/page.tsx` + `components/SeriesCard.tsx`. cover 우선 → 첫 포스트 thumbnail fallback → placeholder. 클릭 → `/series/{id}`.

`app/users/[id]/page.tsx` 탭 목록에 "시리즈" 탭 추가 (존재 탭 구조 확인 후 결정).

### F-11. 피드 카드 visibility 인디케이터

```tsx
function VisibilityBadge({ visibility }) {
  if (visibility === "public") return null;
  return (
    <span className="absolute top-2 right-2 ..." title={...}>
      {visibility === "followers_only" ? <LockClosedIcon /> : <LinkIcon />}
    </span>
  );
}
```

`comments_enabled === false`: 댓글 영역에 "댓글이 비허용된 게시물입니다" 메시지.

### F-12. Form State 통합 (5 통합 지점 회귀 0)

`usePostFormState.ts` + `useDraftAutosave.ts` 신규 3 필드 (optional). `resetFromDraft`에 `?? default` 적용 (legacy drafts 자동 default). localStorage round-trip JSON 안전.

| 통합 지점 | 변경 | 회귀 |
|-----------|------|:---:|
| useDraftAutosave | optional 필드 추가 | 0 |
| DraftRestoreDialog | `?? default` | 0 |
| 멀티탭 sync | JSON round-trip | 0 |
| role-gating | role 검사 없음 | 0 |
| useArtistGate | zero coupling | 0 |

### F-13. handleSubmit 갱신 (page.tsx)

기존 `createPost()`를 `publishPost(draftId, {...})`로 변경. draft 먼저 저장 → publish 패턴:
```typescript
let draftId = currentDraftId ?? await saveToServer();
const result = await publishPost(draftId, {
  publish_at: scheduledAt || null,
  visibility, comments_enabled: commentsEnabled, series_ids: seriesIds,
});
clearDraft();
router.push(result.status === "scheduled" ? `/posts/${result.id}?scheduled=1` : `/posts/${result.id}`);
```

`mapPublishError(e)` — 6 에러 코드 i18n 매핑 (mirror `mapTransformError`).

### F-14. i18n 신규 키 (~42 keys × 5 locales = 210 entries)

- `post.editor.publishOptions.{title, visibility.*, comments.*, series.*, scheduled.*}` ~22 keys
- `post.editor.error.{seriesNotFound, seriesNotOwner, scheduledAtTooSoon, scheduledAtTooFar, postInvalidState, commentsDisabled, auctionActiveVisibilityLocked}` ~7 keys
- `post.editor.wizard.steps.publishOptions` 1 key
- `post.series.{title, postCount, edit, addPost, removePost, empty, byAuthor, createModal.*}` ~10 keys
- `post.feed.indicator.{followersOnly, unlisted, commentsDisabled}` 3 keys

총 42 keys × 5 = **210 entries**.

### F-15. 5 통합 지점 회귀 검증 + Implementation Order PR3-5

| 통합 지점 | 검증 방법 | 기대 |
|-----------|----------|------|
| useDraftAutosave | `visibility="followers_only"` → 2초 → localStorage 확인 | 통과 |
| DraftRestoreDialog | 값 설정 → 새로고침 → restore → 복원 확인 | 통과 |
| 멀티탭 sync | 탭A에서 변경 → 탭B에 multiTabWarning | 통과 |
| role-gating | artist/non-artist/admin 모두 접근 가능 | 통과 |
| useArtistGate | `PublishOptionsPanel` 렌더에 영향 없음 | 통과 |

**Frontend Implementation Order (PR3-5, ~6일)**:

- **PR3 (3일)**: api.ts 타입+client + DraftState + usePostFormState + useMySeries + PublishOptionsPanel + SeriesCreateModal + wizard step 통합 + EditorWorkspace sidebar + handleSubmit + i18n 28 keys
- **PR4 (2일)**: `/series/[id]` + `/users/[id]/series` + SeriesCard + dnd-kit 재사용 + edit mode + i18n 14 keys
- **PR5 (1일)**: VisibilityBadge + comments_disabled 메시지 + 5 통합 지점 회귀 검증 + tsc clean

### F-16. Frontend Risks

| ID | 리스크 | 영향 | 완화 |
|----|--------|:---:|------|
| R-FE-1 | visibility 인디케이터 카드 레이아웃 깨짐 | Low | 16px 아이콘 + `absolute` 포지셔닝 |
| R-FE-2 | drag-reorder 시 drop마다 API 호출 비효율 | Medium | "저장" 버튼 클릭 시만 호출 |
| R-FE-3 | `datetime-local` Safari/모바일 차이 | Medium | `min`/`max` attribute + ISO fallback + TZ 텍스트 |
| R-FE-4 | cover_url null fallback이 GIF 첫 프레임 | Low | `thumbnail_url` 우선 (정지) |
| R-FE-5 | scheduledAt 이중 입력 (MediaToolbar + Picker) | Medium | Panel mount 시 MediaToolbar schedule 버튼 disabled |
| R-FE-6 | wizard step union 확장 시 switch exhaust 누락 | Low | `EditorMobileWizard` 명시 분기 + `never` guard |

---

## 11. New Open Questions for Design Phase (OQ-D) — ✅ ALL RESOLVED (v1.1, 2026-05-03)

| ID | 영역 | 결정 | 영향 |
|----|------|------|------|
| **OQ-D-1 = A** | Backend | `_check_auction_visibility_lock` 적용 (#4 패턴 정신) | publish_post 6단계 권한 흐름에 5번째 단계로 포함 |
| **OQ-D-2 = A** | F+B | PublishOptionsPanel mount 시 MediaToolbar schedule 버튼 비활성 | UX 일관성 + 동일 state 공유 |
| **OQ-D-3 = A** | Frontend | Series reorder = 명시 "저장" 버튼만 API 호출 | R-FE-2 완화, 단순 명료 |
| **OQ-D-4 = A** | Frontend | 작가 프로필 시리즈 = 별도 `/users/{id}/series` 라우트 | Server Component 캐싱 + loading.tsx 분리 |
| **OQ-D-5 = A** | Backend | `GET /series/{id}` 본 PDCA에서는 `status='published'`만 노출 | 단순화, Phase 4 #10에서 viewer 권한 정교화 |

> 5/5 모두 권장 default 채택 (사용자 결정 2026-05-03). **Design v1.1 → /pdca do 진입 가능.**

---

## 12. Test Strategy 통합

| 영역 | 검증 |
|------|------|
| Backend 단위 | 10개 (visibility filter 4 + publish_at validator 3 + comments lock 1 + series owner 1 + cascade 1) |
| Backend 통합 | 12개 (publish 7 + series CRUD 5) |
| Backend Smoke | `smoke_test_publish_controls.sh` 5단계 + `smoke_test_series.sh` 4단계 |
| Frontend 5 통합 지점 | PR3 + PR5 두 번 검증 |
| Frontend Viewport | 375 / 768 / 1024 / 1280 |
| Frontend 5 locale | ko / en / ja / zh / es (~42 keys × 5 = 210 entries) |
| End-to-end | draft 생성 → publish (visibility=followers_only + comments=false + series 1 + scheduled +1h) → DB 확인 → 재진입 시 복원 |

---

## 13. Implementation Order 통합

| Step | 영역 | 작업 | 기간 |
|------|------|------|:---:|
| 1 | Backend | alembic 0039 + 0040 + 모델 + Pydantic schemas + rate_limit + Series CRUD + visibility filter + comments lock | 3일 |
| 2 | Backend | `POST /v1/posts/{id}/publish` + audit log + `_check_auction_visibility_lock` + `_replace_post_series` + 22 tests + 2 smoke | 2일 |
| 3 | Frontend | api.ts 타입+client + DraftState + usePostFormState + useMySeries + PublishOptionsPanel + SeriesCreateModal + wizard step + EditorWorkspace sidebar + handleSubmit + i18n 28 keys | 3일 |
| 4 | Frontend | `/series/[id]` + `/users/[id]/series` + SeriesCard + dnd-kit reorder + edit mode + i18n 14 keys | 2일 |
| 5 | Frontend | VisibilityBadge + comments_disabled UI + 5 통합 지점 회귀 + tsc clean | 1일 |

총 **11일** (Backend 5 + Frontend 6). Backend Step 1과 Frontend Step 3 일부(타입+client) 병렬 가능 → 단축 9-10일.

---

## 14. Risks Summary

가장 큰 위험: **R-1 (인덱스 부재) + R-6/R-FE-2 (소유자 검증 + drag reorder)**. Step 1 0039 인덱스 + Step 2 `_check_series_owner` + Step 4 명시 저장 버튼이 모두 필수.

| 영역 | 핵심 위험 | 완화 |
|------|-----------|------|
| Backend | R-1 visibility 인덱스 | 0039 복합 인덱스 + EXPLAIN 검증 |
| Backend | R-6 series owner 누락 | 헬퍼 호출 강제 + smoke OTHER_TOKEN cross-check |
| Backend | R-4 scheduled_at TZ | UTC 강제 + 5분 버퍼 |
| Frontend | R-FE-2 reorder API 비효율 | "저장" 버튼만 호출 |
| Frontend | R-FE-5 scheduledAt 이중 경로 | MediaToolbar 비활성 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-03 | Initial draft. bkit:bkend-expert (B-1~B-14) + bkit:frontend-architect (F-1~F-16) 병렬 위임 → 통합. 10 OQ resolved (Plan v1.0) + 5 OQ-D surface. alembic 0039+0040 + Series 모델 + publish endpoint + PublishOptionsPanel + dnd-kit 재사용 + 5 통합 지점 회귀 0 명세. | itpe-ince + Claude Opus 4.7 (통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션) |
| 1.1 | 2026-05-03 | OQ-D 5/5 모두 권장 default 일괄 수락 (사용자 결정). §11 OQ-D 표를 결정 echo로 변환, 본문 내용 모두 권장값 기반 그대로 유효. /pdca do 진입 가능. | itpe-ince |
