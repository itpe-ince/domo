---
template: design
version: 1.0
feature: editor-media-ux
sub-pdca: "#4"
date: 2026-05-01
author: itpe-ince (Claude Opus 4.7 + bkit:bkend-expert + bkit:frontend-architect agents)
project: domo
project_version: v1
parent_plan: editor-media-ux.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
---

# editor-media-ux Design Document

> **Summary**: 미디어 카드 drag-reorder(`@dnd-kit/*`), 캡션 입력(`MediaAsset.caption` 컬럼 + 280자 제한), 다중 업로드 진행률 UI 추가. backend·frontend 양면 변경 PDCA.
>
> **Status**: Draft v1.0
> **Sub-PDCA**: #4 (Critical Path)
> **Plan v0.2**: [editor-media-ux.plan.md](../../01-plan/features/editor-media-ux.plan.md)
> **Parent Roadmap**: [editor-revamp-roadmap.plan.md](../../01-plan/features/editor-revamp-roadmap.plan.md)

---

## 0. OQ Resolution Echo (Plan v0.2 사용자 결정)

| ID | 결정 | 영향 영역 |
|----|------|-----------|
| OQ-1 = A | 캡션 입력 — 카드 아래 inline textarea (항상 노출) | Frontend §F-8 |
| OQ-2 = B | 다중 업로드 — `Promise.all` 병렬 | Frontend §F-5 |
| OQ-3 = A | 캡션은 draft에 포함, 발행 시 서버 전달. PATCH는 발행 후 편집 전용 | Backend §B-5, Frontend §F-6 |
| OQ-4 = A | drag handle — dots-grip 아이콘 카드 좌측 상단, dnd-kit Pointer+Touch sensor | Frontend §F-7 |
| OQ-5 = B | 캡션 280자 제한 — schema 검증 | Backend §B-2.1, §B-4 / Frontend §F-8.2 |
| OQ-6 = A (조건부) | 발행된 미디어도 소유자 caption 수정 가능. **단 auction 진행 중 정책은 OQ-D-1로 surface 의무** | Backend §B-7 |
| OQ-7 = A | `MediaUploadProgress` — `MediaToolbar` 직후 고정 배지 | Frontend §F-9 |

---

## 1. Goals & Non-Goals

### 1.1 Goals

1. 작가가 다중 미디어를 업로드한 뒤 **drag-and-drop으로 순서 변경** 가능 (데스크탑 마우스 + 모바일 long-press + 키보드 reorder 모두 지원).
2. 각 미디어에 **선택적 캡션** 280자 한도 — 작품 의도·매체·작업 메모 등을 카드별로 부여.
3. 다중 파일 업로드 시 **파일별 진행 상태**를 시각적으로 표시 (병렬 업로드 + 요약 배지).
4. 캡션은 **draft autosave 흐름에 자연 통합** — 별도 서버 trip 없이 발행 시점에 일괄 저장.
5. 발행 후에도 소유자가 캡션을 수정할 수 있는 **`PATCH /v1/media/{id}` 엔드포인트** 제공 (단 auction 정책은 OQ-D-1).
6. 5개 통합 지점(autosave / DraftRestoreDialog / 멀티탭 / role-gating / useArtistGate) **회귀 0**.
7. 5 locale i18n 동시 출시 (ko/en/ja/zh/es).

### 1.2 Non-Goals

| 항목 | 분리된 PDCA |
|------|-------------|
| 미디어 자체 편집 (crop, filter, 이미지 보정) | #6 `editor-media-studio` |
| 영상 트리밍 / 메이킹 영상 모달 | #6 |
| 외부 임베드(`external_embed`) 캡션 | 후속 — 본 PDCA는 image/video에만 적용 |
| 캡션 마크다운 / 리치텍스트 | 후속 — 평문만 |
| 본문 마크다운 | #5 `editor-rich-content` |
| 발행 옵션(공개범위/예약/시리즈) | #8 `publish-controls` |
| `EditorWorkspace` props drilling 구조 개편 | 후속 (Context 도입은 #7 또는 #8 완료 후 검토) |
| 업로드 실패 retry 버튼 UI | 후속 PDCA |
| 실제 업로드 progress 추적 (XHR 전환) | 후속 PDCA (본 PDCA는 mock 50%/100% — OQ-D-3 참조) |

---

## 2. Architecture Overview

### 2.1 데이터 흐름

```
[User uploads files]
   ↓ FileList
[useMediaUploadQueue.enqueue(files)] ── Promise.all 병렬 ──→ POST /v1/media/upload (×N)
   ↓ UploadTask[] (id, status, progress)            ↓ UploadedMedia[]
[MediaUploadProgress 배지]                       [CreatePostMedia[] (caption=undefined)]
                                                    ↓
[setters.setMedia(prev => [...prev, ...new])] → formState.media
                                                    ↓
[SortableMediaCard 렌더] ←─────────────── DraftState (caption 포함)
   ↓ caption textarea onChange
   ↓ drag-end onReorder(activeId, overId)
   ↓ remove onRemove(id)
[setters.setMedia(arrayMove(...) | mapCaption | filter)]
   ↓ formState 변경
[useDraftAutosave 2s debounce] → localStorage write + (optional) POST /v1/posts/drafts
   ↓ 사용자 발행 클릭
[POST /v1/posts] body: { media: [...], ... }
   ↓ backend posts.py:247
[INSERT media_assets (..., caption=m.caption, order_index=idx)]

[발행 후 캡션 수정]
[PATCH /v1/media/{id}] body: { caption: "..." }
   ↓ backend media.py
[권한 + auction 정책 (OQ-D-1) 검증 → UPDATE]
```

### 2.2 컴포넌트 트리 (Frontend)

```
app/posts/new/page.tsx (CreatePostPageInner)
  ├── [≥ md] EditorWorkspace
  │     ├── MediaToolbar (변경 없음)
  │     ├── MediaPreviewList (재작성)
  │     │     ├── MediaUploadProgress (신규)
  │     │     └── DndContext
  │     │           └── SortableContext
  │     │                 └── SortableMediaCard × N (신규)
  │     │                       ├── DragHandle (DragHandleIcon, 신규)
  │     │                       ├── 미디어 프리뷰 (img / video / external)
  │     │                       ├── progress overlay
  │     │                       ├── Remove button
  │     │                       └── caption textarea (신규)
  │     │     └── OEmbedCard × N (변경 없음)
  │     └── ProductFields (변경 없음)
  │
  └── [< md] EditorMobileWizard → EditorStepContent (step 2)
        ├── MediaToolbar (변경 없음)
        └── MediaPreviewList (동일 컴포넌트, 재사용)
```

### 2.3 백엔드 변경 파일

5개 파일 변경:
- `v1/backend/alembic/versions/0036_media_caption.py` (신규)
- `v1/backend/app/models/post.py` (`MediaAsset.caption` 컬럼)
- `v1/backend/app/schemas/post.py` (`MediaAssetIn.caption` + `MediaPatchRequest`)
- `v1/backend/app/api/posts.py` (`MediaAsset` 생성 시 caption pass-through)
- `v1/backend/app/api/media.py` (`PATCH /{media_id}` 신규 엔드포인트)
- `v1/backend/app/core/rate_limit.py` (`media_patch` scope 추가)

---

## 백엔드 설계 (B 섹션)

> 출처: `bkit:bkend-expert` agent (병렬 작성)

### B-1. Backend 변경 개요 + Out-of-Scope

본 PDCA에서 백엔드는 `media_assets` 테이블에 `caption` 텍스트 컬럼을 추가하고(Alembic 마이그레이션 `0036_media_caption.py`), 발행 시 caption이 `POST /v1/posts` 경로를 통해 `MediaAsset` 행에 저장될 수 있도록 `posts.py`의 MediaAsset 생성 로직을 갱신하며, 발행 후 소유자가 caption을 수정할 수 있는 `PATCH /v1/media/{id}` 엔드포인트를 `media.py`에 신규 추가한다. 변경 대상 파일은 `models/post.py`, `schemas/post.py`, `api/posts.py`, `api/media.py`, `alembic/versions/0036_media_caption.py` 총 5개이며, 나머지 백엔드 인프라(인증, 스토리지, 미디어 업로드 파이프라인, oEmbed, 파일 서빙, 경매/입찰/주문 흐름, 알림 발송 로직)는 변경하지 않는다. `order_index` 갱신 전용 API 역시 본 PDCA 범위 밖이다 — 발행 시 `media[]` 배열 순서가 `order_index`로 그대로 저장되는 기존 패턴(`posts.py:259`)을 유지한다.

### B-2. 데이터 모델 변경

#### B-2.1 `MediaAsset` 모델 — `caption` 컬럼 추가

[v1/backend/app/models/post.py](../../../backend/app/models/post.py) 의 `MediaAsset` 클래스(현재 line 72-108)에 다음 컬럼을 추가:

```python
caption: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
```

| 항목 | 결정 | 근거 |
|------|------|------|
| SQLAlchemy 타입 | `Text` | 평문 최대 280자. VARCHAR(280) 대신 Text로 선언하여 향후 제한값 변경 시 DDL 마이그레이션 불요 |
| nullable | `True` | 캡션은 선택. 기존 미디어 행은 NULL 유지 |
| default | `None` | Python-side 기본값. DB-side `server_default` 불필요 |
| 280자 제한 | 컬럼 레벨 제약 없음 | Pydantic schema 레벨에서 `max_length=280` (OQ-5=B). 향후 제한 변경 시 마이그레이션 불요 |

`is_making_video` 컬럼 이후, `storage_provider` 컬럼 이전에 삽입.

#### B-2.2 인덱스 필요성

`caption`은 검색/필터/정렬 키로 사용 안 됨. 인덱스 불요. 향후 전문 검색이 필요하면 별도 sub-PDCA에서 GIN + `to_tsvector` 도입.

### B-3. Alembic 마이그레이션 (`0036_media_caption.py`)

- **revision ID**: `0036_media_caption`
- **down_revision**: `0035_draft_limit_index`
- **원칙**: additive — 기존 데이터 보존
- **주의**: downgrade 시 caption 데이터 영구 삭제 (§B-13 BR-1)

```python
"""Add caption column to media_assets — editor-media-ux PDCA #4.

Revision ID: 0036_media_caption
Revises: 0035_draft_limit_index
Create Date: 2026-05-01
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0036_media_caption"
down_revision: Union[str, None] = "0035_draft_limit_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "caption",
            sa.Text(),
            nullable=True,
            comment="Optional per-media caption (max 280 chars enforced at schema level)",
        ),
    )


def downgrade() -> None:
    # WARNING: Drops all caption data irreversibly.
    op.drop_column("media_assets", "caption")
```

### B-4. Pydantic Schema 변경

#### B-4.1 `MediaAssetIn` (= `MediaAssetOut` 부모)

```python
class MediaAssetIn(BaseModel):
    type: str
    url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_sec: int | None = None
    size_bytes: int | None = None
    external_source: str | None = None
    external_id: str | None = None
    is_making_video: bool = False
    caption: str | None = Field(None, max_length=280)  # 신규
```

#### B-4.2 `MediaAssetOut`

`MediaAssetIn` 상속으로 caption 자동 노출. 코드 변경 없음.

#### B-4.3 신규 `MediaPatchRequest`

```python
class MediaPatchRequest(BaseModel):
    caption: str | None = Field(None, max_length=280)
```

PATCH 전용 부분 업데이트 schema. `MediaAssetIn` 서브셋 아닌 독립 schema 권장 (필수 필드 의미론 충돌 방지).

### B-5. 신규 엔드포인트: `PATCH /v1/media/{id}`

| 항목 | 값 |
|------|---|
| 메서드 | `PATCH` |
| 경로 | `/v1/media/{id}` |
| 요청 | `MediaPatchRequest` |
| 응답 | `{"data": MediaAssetOut}` |
| 인증 | Bearer token 필수 |
| Rate limit | `media_patch` (분당 30회/사용자) |

**권한 체크 흐름**:
1. `get_current_user` → user (401)
2. `MediaAsset` 조회 → 404 (`MEDIA_NOT_FOUND`)
3. `media.post.author_id != user.id` → 403 (`MEDIA_NOT_OWNER`)
4. **OQ-D-1 분기** (§B-7) — auction 진행 중 정책
5. caption 갱신 + commit + structured log
6. `MediaAssetOut` 반환

```python
@router.patch("/{media_id}")
async def patch_media(
    media_id: UUID,
    body: MediaPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_patch"),
):
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise ApiError("MEDIA_NOT_FOUND", "Media asset not found", http_status=404)

    post_result = await db.execute(select(Post).where(Post.id == media.post_id))
    post = post_result.scalar_one_or_none()
    if not post or post.author_id != user.id:
        raise ApiError("MEDIA_NOT_OWNER", "You can only edit your own media", http_status=403)

    # OQ-D-1: auction 정책 (Step 2에서 결정 후 구현)
    await _check_auction_media_lock(db, post)  # 옵션 A 채택 시

    before_len = len(media.caption) if media.caption else 0
    media.caption = body.caption
    after_len = len(body.caption) if body.caption else 0

    await db.commit()
    await db.refresh(media)

    log.info("media.caption.updated", extra={
        "event": "media.caption.updated",
        "user_id": str(user.id),
        "media_id": str(media.id),
        "post_id": str(media.post_id),
        "caption_before_len": before_len,
        "caption_after_len": after_len,
    })

    return {"data": MediaAssetOut.model_validate(media)}
```

### B-6. `POST /v1/posts` 본문 변경 (caption pass-through)

[v1/backend/app/api/posts.py](../../../backend/app/api/posts.py) line 245-261의 `MediaAsset` 생성 루프에 `caption=m.caption` 추가.

```python
for idx, m in enumerate(body.media):
    db.add(
        MediaAsset(
            post_id=post.id,
            type=m.type,
            url=m.url,
            # ... 기존 필드 ...
            order_index=idx,
            caption=m.caption,  # 신규: OQ-3=A draft 경유, None 안전 fallback
        )
    )
```

**회귀 안전**: `MediaAssetIn.caption=Field(None, max_length=280)` optional. 기존 클라이언트 `caption` 미전송 시 `None` → DB NULL 정상 저장.

### B-7. 권한·발행 정책 — OQ-6 + 신규 OQ-D-1

#### OQ-6=A 결정 반영

발행된 미디어도 소유자라면 PATCH 가능. 발행 상태 게이트 없음 — 소유권 검증만으로 충분.

#### OQ-D-1 정의 — Auction 진행 중 Caption 수정 정책

**질문**: `auction.status='active'`인 product post의 미디어 caption 수정 시 동작?

**옵션 비교**:

| 옵션 | 동작 | 장점 | 단점 |
|------|------|------|------|
| **A — 차단** (권장) | `AUCTION_ACTIVE_MEDIA_LOCKED` (409) 반환 | 입찰자 신뢰 보호. 입찰 근거 불변 | 작가 오탈자 수정 불가 |
| B — 허용 + 알림 | 입찰자 모두에게 `Notification` + audit log | 투명성 | 구현 복잡 (입찰자 조회 + 알림 트랜잭션) |
| C — 허용 (조용히) | audit log만 | 단순 | 입찰자가 변경 사실 인지 불가 |

**권장 default: 옵션 A (차단)**.

근거:
- 예술 작품 거래 — 입찰자가 특정 캡션을 보고 입찰했을 수 있음. 사후 변경은 입찰 근거 변조
- 옵션 B 알림은 투명하나, "변경 허용" 자체가 신뢰 문제
- 경매 종료 후 수정 가능하므로 작가 편의 완전 차단 아님
- OWASP — 최소 권한 원칙

**비-auction product (단순 buy-now)**: 별도 잠금 없음, caption 수정 허용. buy-now `pending_payment` Order 존재 시도 허용 (단일 구매자 영향). 향후 엄격 정책 필요 시 별도 OQ.

**옵션 A 채택 시 헬퍼 코드** (Step 2에서 삽입):

```python
async def _check_auction_media_lock(db: AsyncSession, post: Post) -> None:
    """OQ-D-1 옵션 A: active auction 미디어 caption 수정 차단."""
    if post.type != "product":
        return
    result = await db.execute(
        select(Auction).where(
            Auction.product_post_id == post.id,
            Auction.status == "active",
        )
    )
    active_auction = result.scalar_one_or_none()
    if active_auction:
        raise ApiError(
            "AUCTION_ACTIVE_MEDIA_LOCKED",
            "미디어 수정은 경매 종료 후 가능합니다",
            details={"auction_id": str(active_auction.id)},
            http_status=409,
        )
```

### B-8. Audit / Logging

**구조화 로그** (Python `logging` + JSON formatter):

```python
log.info("media.caption.updated", extra={
    "event": "media.caption.updated",
    "user_id": str(user.id),
    "media_id": str(media.id),
    "post_id": str(media.post_id),
    "caption_before_len": before_len,
    "caption_after_len": after_len,
})
```

**`UserActivityLog` 비채택**: 추천 엔진 데이터 수집 목적 모델([v1/backend/app/models/activity_log.py](../../../backend/app/models/activity_log.py))로, caption 수정 audit과 의미 충돌. 향후 audit trail이 법적 요건이 되면 별도 `media_caption_audit_logs` 테이블 도입.

### B-9. Rate Limiting

[v1/backend/app/core/rate_limit.py](../../../backend/app/core/rate_limit.py) `DEFAULT_LIMITS`:

```python
"media_patch": {"limit": 30, "window_sec": 60, "by": "user"},
```

근거: 캡션은 짧은 텍스트 수정 — 업로드(`media_upload: 20/min`)보다 관대. 분당 30회는 악용 방지 + 정상 UX 충분. `by: "user"` (인증 필수 엔드포인트).

### B-10. Error Codes

| 코드 | HTTP | 발생 조건 |
|------|------|-----------|
| `MEDIA_NOT_FOUND` | 404 | media_id 없음 |
| `MEDIA_NOT_OWNER` | 403 | post.author_id ≠ user.id |
| `MEDIA_CAPTION_TOO_LONG` | 422 | 280자 초과 (Pydantic 자동) |
| `AUCTION_ACTIVE_MEDIA_LOCKED` | 409 | OQ-D-1 옵션 A 채택 시 |

### B-11. Test Strategy (Backend)

**단위 테스트** (`tests/api/test_media_patch.py`):
- `test_owner_can_update_caption` (200)
- `test_owner_can_clear_caption` (caption=None → DB NULL)
- `test_caption_too_long_rejected` (281자 → 422)
- `test_non_owner_forbidden` (403)
- `test_nonexistent_media_404` (404)
- `test_unauthenticated_rejected` (401)
- `test_rate_limit_enforced` (31회 → 429)
- `test_active_auction_blocks_caption_edit` (OQ-D-1=A 시 409)

**통합 테스트** (`tests/integration/test_post_publish_with_caption.py`):
- `test_publish_post_with_caption_saved` (POST /v1/posts → DB caption 저장)
- `test_publish_post_without_caption_is_null` (caption 미전송 → NULL, 회귀 0)

**Alembic 검증**:
```bash
alembic upgrade 0036_media_caption
psql -c "\d media_assets"  # caption text 확인
alembic downgrade 0035_draft_limit_index  # 컬럼 drop 확인
alembic upgrade head  # 재적용 (downgrade 손실 데이터 복구 불가 경고)
```

**Smoke test** (`scripts/smoke_test_media_caption.sh`): upload → publish with caption → PATCH → 타인 PATCH 403 → 281자 422.

### B-12. Backend Implementation Order

#### Step 1 — DB + 모델 + Schema + caption pass-through (PATCH 제외)
1. `0036_media_caption.py` 마이그레이션
2. `MediaAsset.caption` 필드
3. `MediaAssetIn.caption` + `MediaPatchRequest`
4. `posts.py` MediaAsset 생성 시 caption pass-through

**완료 후 회귀 검증**:
- 기존 `POST /v1/posts` (caption 없는 요청) → 200
- caption 미전송 → DB NULL
- caption 포함 → DB 저장
- alembic upgrade/downgrade 왕복

#### Step 2 — PATCH 엔드포인트 + OQ-D-1 결정 후 정책 구현

**전제**: OQ-D-1 사용자 결정 완료.

1. `core/rate_limit.py` `media_patch` scope
2. `api/media.py` PATCH 엔드포인트
3. OQ-D-1=A 채택 시 `_check_auction_media_lock` 헬퍼
4. 단위 테스트
5. Smoke test

### B-13. Backend Risks

| ID | 위험 | 영향 | 대응 |
|----|------|:---:|------|
| BR-1 | Alembic downgrade 시 caption 데이터 영구 손실 | High | downgrade 전 `pg_dump` 백업 의무화. 프로덕션 downgrade 사전 승인 절차 |
| BR-2 | OQ-D-1 미결 시 auction 정책 누락 — data integrity 문제 | High | Step 2 배포 전 OQ-D-1 결정 완료 필수. placeholder 코드 교체 게이트 |
| BR-3 | 클라이언트 schema 우회 입력으로 280자 초과 저장 | Medium | Pydantic FastAPI validation pipeline 자동. 미래 직접 DB 접근 시 CHECK constraint 검토 |
| BR-4 | `POST /v1/posts` 회귀 — caption 없는 기존 클라이언트 | Medium | Optional 필드 + None fallback. `test_publish_post_without_caption_is_null` 검증 |
| BR-5 | OWASP A01 Broken Access Control — PATCH 권한 검증 버그 | High | `post.author_id == user.id` 검증 우선. 단위 테스트 게이트 |

---

## 프런트엔드 설계 (F 섹션)

> 출처: `bkit:frontend-architect` agent (병렬 작성)

### F-1. Frontend 변경 개요 + Out-of-Scope

본 PDCA의 프런트엔드 변경은 세 축: (1) `@dnd-kit/core` + `@dnd-kit/sortable` 설치 — 프로젝트 최초 외부 React 라이브러리 도입. (2) [MediaPreviewList.tsx](../../../frontend/src/components/post-editor/MediaPreviewList.tsx)(현재 70줄)를 `DndContext`/`SortableContext` 기반으로 전면 재작성하고 `SortableMediaCard`/`MediaUploadProgress` 두 컴포넌트 신규 추가. (3) `useMediaUploadQueue` hook으로 page.tsx의 `for...of` 순차 업로드를 `Promise.all` 병렬로 대체. 캡션은 `CreatePostMedia.caption?` 옵션 필드로 `DraftState.media[]`에 자연 통합되어 `useDraftAutosave` 코드 자체 변경 0.

### F-2. 의존성 도입

#### F-2.1 패키지

```json
{
  "dependencies": {
    "@dnd-kit/core": "^6.3.1",
    "@dnd-kit/sortable": "^8.0.0",
    "next": "15.0.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  }
}
```

`@dnd-kit/utilities`는 peer 자동 설치. `arrayMove`는 `@dnd-kit/sortable` re-export.

#### F-2.2 번들 크기 영향 (추정 — 측정 후 결정)

| 패키지 | gzip 추정 |
|--------|:--------:|
| `@dnd-kit/core@6.x` | ~11 KB |
| `@dnd-kit/sortable@8.x` | ~4 KB |
| `@dnd-kit/utilities` (indirect) | ~1 KB |
| **합계** | **~16 KB** |

허용 임계: gzip 20 KB 이하. Do 단계에서 `next build` 출력 측정.

#### F-2.3 React 19 호환성

현재 `react@^18.3.1`. dnd-kit 6.x는 React 16+ 공식 지원. React 19 업그레이드 시 concurrent render + dnd-kit useReducer 충돌 검증 필요. 본 PDCA는 React 18에서 진행 — 즉각 위험 없음.

#### F-2.4 SSR Hydration (Next.js 15 App Router)

dnd-kit은 client-only. 모든 신규 컴포넌트에 `"use client"` 명시. `MediaPreviewList`가 이미 client 컴포넌트 → 추가 `dynamic({ ssr: false })` 래핑 불필요할 가능성 높음. **Step 3 시작 직후 최소 샘플(카드 1개 drag)로 hydration warning 유무 검증**.

### F-3. 컴포넌트 트리 (반복 — §2.2 참조)

### F-4. 신규 컴포넌트 카탈로그

#### `SortableMediaCard.tsx`
- 위치: `v1/frontend/src/components/post-editor/SortableMediaCard.tsx`
- 책임: 개별 미디어 카드 — drag handle(좌측 상단) + 미디어 프리뷰 + progress overlay + remove + caption textarea(항상 노출)
- props:
  ```ts
  interface SortableMediaCardProps {
    id: string;             // crypto.randomUUID() — DndContext 식별자
    media: CreatePostMedia;
    index: number;          // aria-label용
    uploadTask?: UploadTask;
    onRemove: (id: string) => void;
    onCaptionChange: (id: string, caption: string) => void;
  }
  ```
- dnd-kit 통합: `useSortable({ id })`. **drag listeners는 handle button에만 attach** (textarea 키보드 이벤트 충돌 방지)

#### `MediaUploadProgress.tsx`
- 위치: `v1/frontend/src/components/post-editor/MediaUploadProgress.tsx`
- 책임: 업로드 큐 요약 배지. 비어있으면 `null` 반환 (DOM 사라짐)
- props: `{ queue: UploadTask[] }`
- 자동 소멸: 모든 success → 2초 후 사라짐. failed 있으면 유지

#### `MediaPreviewList.tsx` (재작성)
- 위치: 기존 파일 전면 재작성
- 책임: `DndContext` + `SortableContext` 래퍼. `MediaUploadProgress` 상단 + `SortableMediaCard × N` + `OEmbedCard × M`
- props (기존 + 신규):
  ```ts
  interface MediaPreviewListProps {
    media: CreatePostMedia[];
    embeds: OEmbedData[];
    onRemoveMedia: (index: number) => void;
    onRemoveEmbed: (index: number) => void;
    // 신규
    onReorder: (activeId: string, overId: string) => void;
    onCaptionChange: (id: string, caption: string) => void;
    uploadQueue: UploadTask[];
  }
  ```

#### `DragHandleIcon` (신규 아이콘)
- 위치: `v1/frontend/src/components/icons.tsx`
- dots-grip SVG 패턴 (3×2 dots)

### F-5. 신규 hook: `useMediaUploadQueue`

위치: `v1/frontend/src/lib/hooks/useMediaUploadQueue.ts`

```ts
export interface UploadTask {
  id: string;            // crypto.randomUUID()
  file: File;
  status: "queued" | "uploading" | "success" | "error";
  progress: number;      // 0-100. fetch 기반 → mock 50%/100% (OQ-D-3)
  error?: string;
  result?: UploadedMedia;
}

function useMediaUploadQueue(): {
  queue: UploadTask[];
  enqueue: (files: FileList | File[], isMakingVideo?: boolean) => Promise<CreatePostMedia[]>;
  enqueueGif: (file: File) => Promise<CreatePostMedia | null>;
  clearCompleted: () => void;
  isUploading: boolean;
}
```

내부 `Promise.all` 병렬 (OQ-2=B). `Promise.allSettled`로 부분 실패 허용 — 성공한 파일만 `CreatePostMedia[]` 반환, 실패는 queue에 error 상태로 잔류.

#### Progress 추적 trade-off (OQ-D-3 후보)

`uploadMediaFile`은 `fetch` 기반 — 업로드 progress 직접 추적 불가. 대안: XHR 전환 + `xhr.upload.onprogress`. 본 PDCA는 mock 50%/100% 채택 (MVP 속도 우선). 실제 progress는 후속 PDCA.

### F-6. 데이터 모델 (Frontend types)

#### F-6.1 `CreatePostMedia`에 `caption?` + `_clientId?` 추가

[api.ts](../../../frontend/src/lib/api.ts) line 1119:

```ts
export type CreatePostMedia = {
  type: "image" | "video" | "external_embed";
  url: string;
  thumbnail_url?: string | null;
  width?: number;
  height?: number;
  duration_sec?: number;
  size_bytes?: number;
  external_source?: string | null;
  external_id?: string | null;
  is_making_video?: boolean;
  // PDCA #4 신규
  caption?: string;
  /** 클라이언트 전용 — 서버 전송 제외. DndContext items 동기화용 */
  _clientId?: string;
};
```

발행 시 page.tsx `handleSubmit`에서 `const { _clientId, ...rest } = m`로 명시적 제거 (Pydantic `extra="forbid"` 가능성 대비).

#### F-6.2 DraftState 자동 통합

`CreatePostMedia`에 `caption` 추가만으로 `DraftState.media[i].caption` 자동 포함. `useDraftAutosave` 코드 변경 없음.

#### F-6.3 기존 localStorage draft 호환성

기존 draft에 `caption` 없음 → `undefined` fallback. SortableMediaCard textarea `value={media.caption ?? ""}` 패턴.

#### F-6.4 신규 `patchMedia()` API 함수

```ts
export interface PatchMediaBody {
  caption?: string;
}

export async function patchMedia(
  mediaId: string,
  body: PatchMediaBody
): Promise<UploadedMedia> {
  return apiFetch<UploadedMedia>(`/media/${encodeURIComponent(mediaId)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}
```

본 PDCA에서 호출 안 함 (OQ-3=A — caption은 draft 흐름). 후속 PDCA에서 호출부 통합.

### F-7. drag-reorder UX

#### F-7.1 DndContext sensors

```tsx
const sensors = useSensors(
  useSensor(PointerSensor, {
    activationConstraint: { distance: 8 },  // 8px 이동 후 drag 시작 (실수 방지)
  }),
  useSensor(TouchSensor, {
    activationConstraint: {
      delay: 200,    // OQ-4=A 200ms long-press
      tolerance: 5,  // long-press 중 5px 미만 흔들림 허용
    },
  }),
  useSensor(KeyboardSensor, {
    coordinateGetter: sortableKeyboardCoordinates,
  })
);
```

#### F-7.2 arrayMove로 state reorder

```tsx
function handleReorder(activeId: string, overId: string) {
  setters.setMedia(prev => {
    const oldIndex = prev.findIndex(m => m._clientId === activeId);
    const newIndex = prev.findIndex(m => m._clientId === overId);
    if (oldIndex === -1 || newIndex === -1) return prev;
    return arrayMove(prev, oldIndex, newIndex);
  });
}
```

reorder → `formState.media` 변경 → `useDraftAutosave` 2s debounce 자동 trigger. 별도 effect 불필요.

#### F-7.3 모바일 long-press timing

`TouchSensor delay: 200ms` (기본 250ms에서 단축, 체감 응답성 향상). `tolerance: 5` 손떨림 허용 + scroll 구분.

### F-8. caption UX

#### F-8.1 inline textarea (OQ-1=A)

각 카드 하단 항상 마운트. 모달/overlay 없음.

#### F-8.2 280자 카운터 (OQ-5=B)

```tsx
const MAX = 280;
const remaining = MAX - (value?.length ?? 0);
const isOverLimit = remaining < 0;

<textarea
  value={value}
  onChange={(e) => onChange(e.target.value)}
  maxLength={MAX + 50}  // soft cap — UI 경고 + 서버 검증 병행
  rows={2}
  className={`...${isOverLimit ? "border-danger" : ""}`}
  placeholder={t("post.editor.media.caption.placeholder")}
/>
<p className={remaining < 0 ? "text-danger" : "text-text-muted"}>
  {remaining}/{MAX}
</p>
```

`maxLength={MAX + 50}` soft cap — `maxLength={MAX}`로 강제 차단 시 사용자 혼란. UI 경고 + 서버 검증이 최종 방어.

#### F-8.3 Multiline

`<textarea rows={2}>` (OQ-D-2 결정 — 권장 A 고정 높이).

#### F-8.4 Placeholder

`t("post.editor.media.caption.placeholder")` — 예: "캡션을 입력하세요... (예: 작품 의도, 매체)"

#### F-8.5 caption 변경 → autosave 자동

`onCaptionChange(id, caption)` → `setters.setMedia(prev.map(m => m._clientId === id ? { ...m, caption } : m))` → `formState.media` 변경 → `useDraftAutosave` 2s debounce. 추가 effect 없음.

**textarea 키보드 이벤트 충돌 방지**: `{...listeners}`(dnd-kit drag listeners)는 drag handle button에만 attach. 카드 컨테이너 div에 spread 금지.

### F-9. MediaUploadProgress UX (OQ-7=A)

#### F-9.1 마운트 위치

`MediaPreviewList` 내부 최상단:

```tsx
<div className="space-y-3">
  <MediaUploadProgress queue={uploadQueue} />
  <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
    <SortableContext items={items} strategy={rectSortingStrategy}>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {media.map((m, i) => <SortableMediaCard key={m._clientId ?? i} ... />)}
      </div>
    </SortableContext>
  </DndContext>
  {embeds.map(...)}
</div>
```

#### F-9.2 표시 형식

`{done}/{total} 업로드 중` → 모두 success → 2초 동안 "업로드 완료" → 사라짐. failed 있으면 유지.

#### F-9.4 Retry 버튼 — 본 PDCA scope 외

실패 시 `MediaUploadProgress`에 `{n}개 실패`만 표시. 사용자는 실패 카드 삭제 후 재업로드. 후속 PDCA에서 retry UX 도입.

### F-10. EditorWorkspace + EditorStepContent 변경

신규 props 3개 (양쪽 동일):
- `onReorder: (activeId, overId) => void`
- `onCaptionChange: (id, caption) => void`
- `uploadQueue: UploadTask[]`

기존 `uploading && <div>업로드 중...</div>` 블록 제거 (`MediaUploadProgress`로 대체).

**Props drilling 평가**: EditorWorkspace 실질 props ~40 → ~43. 본 PDCA Context 도입 없음. #7 또는 #8 완료 후 EditorContext 도입 검토.

### F-11. i18n Keys (`post.editor.media.*`)

11개 키 × 5 locale = 55 entries.

| 키 | ko | en |
|----|----|----|
| `caption.placeholder` | 캡션을 입력하세요... (예: 작품 의도, 매체) | Add a caption... (e.g. intent, medium) |
| `caption.counter` | `{{remaining}}/280` | `{{remaining}}/280` |
| `caption.tooLong` | 280자를 초과했습니다 | Exceeds 280 characters |
| `caption.label` | 캡션 | Caption |
| `dragHandle.aria` | 순서 변경 핸들 | Drag to reorder |
| `reorder.aria` | {{index}}번째 미디어 | Media item {{index}} |
| `upload.progress` | {{done}}/{{total}} 업로드 중 | Uploading {{done}}/{{total}} |
| `upload.complete` | 업로드 완료 | Upload complete |
| `upload.failed` | {{n}}개 업로드 실패 | {{n}} upload(s) failed |
| `uploading` | 업로드 중... | Uploading... |
| `remove.aria` | 미디어 삭제 | Remove media |

ja/zh/es 번역도 동일 구조로 5 locale 동시 출시.

ICU 보간 구문(`{{varName}}`)은 기존 `post.draft.lastSavedAgo` 패턴 따름.

### F-12. Accessibility

- **F-12.1 키보드 reorder**: dnd-kit `KeyboardSensor` + `sortableKeyboardCoordinates`. Tab→handle 포커스, Space=grab/drop, Arrow=이동, Esc=취소
- **F-12.2 ARIA**: `useSortable.attributes`가 `role="button"`/`tabindex=0`/`aria-pressed`/`aria-roledescription="sortable"`/`aria-describedby` 자동 주입
- **F-12.3 prefers-reduced-motion**: `window.matchMedia("(prefers-reduced-motion: reduce)").matches` 검사하여 dnd-kit transition null 처리
- **F-12.4 caption label**: `<label className="sr-only" htmlFor={id}>` + `<textarea id={id}>`

### F-13. Performance

- **F-13.1 SortableMediaCard React.memo**: drag-reorder 중 불필요 re-render 방지. `onRemove`/`onCaptionChange`는 호출부 `useCallback`으로 안정화 필수
- **F-13.2 caption debounce**: 기존 useDraftAutosave 2s debounce에 흡수
- **F-13.3 virtualization**: 미디어 ≤ 10개 예상 — 도입 안 함

### F-14. Test/Verification Strategy (Frontend)

#### F-14.1 자동 테스트 부재

수동 시나리오로 진행 (jest/vitest/playwright 미설치).

#### F-14.2 5 통합 지점 회귀 체크리스트

| # | 지점 | 시나리오 |
|---|------|----------|
| 1 | useDraftAutosave | caption 입력 → 2s 후 localStorage `domo-draft-*`에 caption 포함 |
| 2 | DraftRestoreDialog | caption 포함 draft 저장 → 재진입 → 복원 다이얼로그 → 카드에 caption 복원 |
| 3 | 멀티탭 storage event | 2탭 동시 편집 → 경고 배너 |
| 4 | PostTypeSelector role-gating | 비작가 product 차단 |
| 5 | useArtistGate | applicationStatus pending 시 product 비활성 + 힌트, fetch 실패 시 fallback |

#### F-14.3 Viewport별

375 / 768 / 1024 / 1280px 모두 정상 동작.

#### F-14.4 5 locale

ko/en/ja/zh/es 전환 시 신규 키 표시. 일본어/중국어 긴 placeholder 레이아웃 유지.

#### F-14.5 키보드 reorder

Tab → Space → Arrow → Space (drop) → autosave 2초 → localStorage 확인. Esc로 취소 → 원위치.

### F-15. Frontend Implementation Order (Step 3-7)

#### Step 3 — 타입 + 의존성 (TS 0에러)
1. `npm install @dnd-kit/core@^6.3.1 @dnd-kit/sortable@^8.0.0`
2. `api.ts`: `CreatePostMedia.caption?` + `_clientId?` + `patchMedia()`
3. `icons.tsx`: `DragHandleIcon`
4. `next build` → 0 에러
5. 구버전 draft 호환성 검증 (수동 LocalStorage 주입)

**회귀 체크**: autosave 5 지점 빠른 검증.

#### Step 4 — 컴포넌트 (dnd-kit drag-reorder 데스크탑 동작)
1. `useMediaUploadQueue.ts`
2. `SortableMediaCard.tsx`
3. `MediaUploadProgress.tsx`
4. `MediaPreviewList.tsx` 재작성
5. `next dev` → SSR hydration warning 검증

**회귀 체크**: 빈 핸들러 임시 연결, autosave 정상.

#### Step 5 — 호출부 연결 (5 통합 지점 회귀 0)
1. `EditorWorkspace.tsx` 신규 props + `MediaPreviewList` 호출 + `uploading` div 제거
2. `EditorStepContent.tsx` 동일
3. `page.tsx`: `handleFiles` → `useMediaUploadQueue.enqueue()` 교체. `handleReorder`/`handleCaptionChange` 작성
4. **5 통합 지점 체크리스트 전체 실행**

#### Step 6 — i18n 5 locale (AC-8)
1. ko/en/ja/zh/es에 `post.editor.media.*` 11키 추가
2. 5 locale 전환 검증

#### Step 7 — 회귀 검증 (AC-1~10 전체 Pass)
1. viewport 4종 수동 테스트
2. 5 locale 수동
3. 키보드 reorder
4. `prefers-reduced-motion`
5. Network throttle 3G + 3개 동시 업로드 → 카드별 progress 독립
6. caption 복원 (DraftRestoreDialog)
7. 구버전 draft 호환성

### F-16. Frontend Risks

| ID | 리스크 | 영향 | 대응 |
|----|--------|:---:|------|
| R-FE-1 | 5 통합 지점 회귀 — MediaPreviewList 대폭 재작성 | High | Step 4 직후 5 지점 체크. Step 5 빈 핸들러 임시 연결 후 동작 확인 |
| R-FE-2 | dnd-kit SSR hydration mismatch (Next.js 15 미검증) | Medium | Step 3 직후 최소 샘플 검증. 발생 시 `dynamic({ ssr: false })` |
| R-FE-3 | 구버전 localStorage draft 호환성 | High | `caption?` optional + textarea `value={... ?? ""}` fallback |
| R-FE-4 | caption textarea 키보드 ↔ dnd-kit 충돌 | High | `{...listeners}` handle button에만 attach |
| R-FE-5 | 모바일 touch drag vs scroll 충돌 | Medium | `delay: 200, tolerance: 5`. 실기기 테스트 후 조정. `restrictToParentElement` 백업 |
| R-FE-6 | EditorWorkspace props ~43개 | Medium | 본 PDCA 유지. 후속 PDCA EditorContext 검토 |
| R-FE-7 | mock 50%/100% progress 사용자 혼란 | Low | spinner + 카운터(`1/3`)로 완화. XHR 전환 후속 |

---

## 11. New Open Questions for Design Phase (OQ-D) — ✅ Resolved (2026-05-02)

| ID | 질문 | A | B | C | 결정 | 영역 |
|----|------|---|---|---|:---:|------|
| **OQ-D-1** | auction `status='active'` 시 caption 수정 정책 | **차단** (`AUCTION_ACTIVE_MEDIA_LOCKED` 409) | 허용 + 입찰자 알림 | 허용 (조용히, audit log만) | **✅ A (차단)** | Backend |
| **OQ-D-2** | caption textarea 높이 — 고정 vs auto-grow | **고정 2 rows** (`rows={2}`, resize-y) | auto-grow (`scrollHeight` 추적) | — | **✅ A (고정)** | Frontend |
| **OQ-D-3** | upload progress 정확도 | mock 50%/100% (`fetch` 유지) | **XHR 전환 + 실제 progress** | — | **✅ B (XHR 실제 추적)** ⚠️ 권장에서 변경 | Frontend |
| **OQ-D-4** | dnd-kit `DragOverlay` 사용 여부 | **사용 안 함** (반투명 카드) | DragOverlay (floating preview) | — | **✅ A (없음, 단순화)** | Frontend |
| **OQ-D-5** | (OQ-1=A로 기결정) — 빈 캡션 카드 표시 | 항상 textarea 노출 (placeholder) | — | — | **✅ A (OQ-1=A 확정)** | Frontend |

### OQ-D-3 = B 변경 영향 (사용자 결정으로 권장 A에서 B로 변경)

**범위 확장**: `uploadMediaFile`을 `fetch` 기반에서 `XMLHttpRequest` 기반으로 리팩토링 — 실제 업로드 progress 추적 활성화.

**§F-5 변경**:
- `UploadTask.progress`는 mock 50%/100%가 아닌 **실제 0~100 값** (XHR `xhr.upload.onprogress`의 `event.loaded / event.total * 100`)
- `useMediaUploadQueue`의 `enqueue` 내부에서 `Promise.all`로 병렬 + 각 파일은 `XMLHttpRequest` 인스턴스로 업로드
- 취소 패턴: `AbortController` 대신 `xhr.abort()` (XHR 네이티브)
- 실패 시 `xhr.onerror` + `xhr.ontimeout` 핸들러
- `apiFetch` 헬퍼 우회 — XHR은 별도 자격증명 헤더 처리 필요 (`Authorization: Bearer {token}` 직접 setRequestHeader)

**§F-15 Step 4 변경**:
- `useMediaUploadQueue.ts` 신규 작성 시 `uploadMediaFile`을 직접 XHR로 호출하는 패턴 채택. **단, 기존 `uploadMediaFile`(api.ts)을 수정하지 않고** wrapper 함수를 hook 내부에 두어 영향 범위를 최소화 (다른 사용처 회귀 0)
- 또는: api.ts에 `uploadMediaFileWithProgress(file, onProgress)` 함수를 추가하고 기존 `uploadMediaFile`은 그 wrapper로 변경 — **이 방식 권장 (단일 진실 원천)**

**§F-16 R-FE-7 제거**: "mock 50%/100% 사용자 혼란" 위험 더 이상 해당 없음 — 실제 progress 표시.

**신규 위험 R-FE-8 (XHR 전환 부수효과)**:
- XHR은 `fetch`보다 보일러플레이트 코드 증가
- 401 자동 refresh 로직(api.ts의 `tryRefreshAccessToken`) 통합 필요 — XHR `onload` 시 401 응답 처리 로직 작성
- 영향: ~50줄 추가 + api.ts에 `uploadMediaFileWithProgress` 함수 추가
- 완화: 단위 테스트 가능한 형태(`onProgress`, `onSuccess`, `onError` 콜백)로 추출

### F-5 Progress 추적 구현 (OQ-D-3=B 적용)

```ts
// v1/frontend/src/lib/api.ts — 신규 함수
export interface UploadProgressEvent {
  loaded: number;
  total: number;
  percent: number; // 0-100
}

export async function uploadMediaFileWithProgress(
  file: File,
  isMakingVideo: boolean,
  onProgress?: (e: UploadProgressEvent) => void
): Promise<UploadedMedia> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("is_making_video", String(isMakingVideo));

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/v1/media/upload`);
    const token = tokenStore.get();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable || !onProgress) return;
      onProgress({
        loaded: e.loaded,
        total: e.total,
        percent: Math.round((e.loaded / e.total) * 100),
      });
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const json = JSON.parse(xhr.responseText);
          resolve(json.data as UploadedMedia);
        } catch (err) {
          reject(new Error("응답 파싱 실패"));
        }
      } else if (xhr.status === 401) {
        // 401 처리: refresh + 1회 재시도 — Step 4 구현 시 결정
        reject(new ApiClientError("UNAUTHORIZED", "인증 만료. 다시 로그인 후 재시도", { status: xhr.status }));
      } else {
        reject(new ApiClientError("UPLOAD_FAILED", `${xhr.status} ${xhr.statusText}`, {}));
      }
    };

    xhr.onerror = () => reject(new ApiClientError("NETWORK_ERROR", "네트워크 오류", {}));
    xhr.ontimeout = () => reject(new ApiClientError("UPLOAD_TIMEOUT", "업로드 시간 초과", {}));

    xhr.send(formData);
  });
}

// 기존 uploadMediaFile은 이 함수의 wrapper로 변경
export async function uploadMediaFile(
  file: File,
  isMakingVideo: boolean
): Promise<UploadedMedia> {
  return uploadMediaFileWithProgress(file, isMakingVideo);
}
```

```ts
// v1/frontend/src/lib/hooks/useMediaUploadQueue.ts — onProgress 통합
const enqueue = useCallback(async (files, isMakingVideo = false) => {
  const fileArr = Array.from(files);
  const newTasks: UploadTask[] = fileArr.map(file => ({
    id: crypto.randomUUID(),
    file,
    status: "queued",
    progress: 0,
  }));
  setQueue(prev => [...prev, ...newTasks]);

  const results = await Promise.allSettled(
    newTasks.map(async (task) => {
      updateTask(task.id, { status: "uploading", progress: 0 });
      try {
        const uploaded = await uploadMediaFileWithProgress(
          task.file,
          isMakingVideo,
          (e) => updateTask(task.id, { progress: e.percent })
        );
        updateTask(task.id, { status: "success", progress: 100, result: uploaded });
        return { taskId: task.id, uploaded };
      } catch (e) {
        const msg = e instanceof Error ? e.message : "업로드 실패";
        updateTask(task.id, { status: "error", error: msg });
        throw e;
      }
    })
  );
  // ... 성공만 CreatePostMedia로 변환 반환
}, [updateTask]);
```

---

## 12. 통합 Test Strategy

| 영역 | 검증 |
|------|------|
| Backend 단위 | `tests/api/test_media_patch.py` 8개 시나리오 |
| Backend 통합 | POST /v1/posts caption 저장·NULL fallback |
| Backend Alembic | upgrade/downgrade/upgrade 왕복 |
| Backend Smoke | curl 기반 5단계 (upload → publish → PATCH → 타인 → 281자) |
| Frontend 5 통합 지점 회귀 | 매 Step 후 체크리스트 |
| Frontend Viewport | 375/768/1024/1280px |
| Frontend 5 locale | ko/en/ja/zh/es 전환 |
| Frontend a11y | 키보드 reorder + prefers-reduced-motion |
| End-to-end | 업로드 3개 동시 → reorder → caption 입력 → draft 저장 → 재진입 복원 → 발행 → DB 확인 |

---

## 13. 통합 Implementation Order

| Step | 영역 | 작업 | 회귀 체크 |
|------|------|------|----------|
| 1 | Backend | 마이그레이션 + 모델 + schema + posts.py caption pass-through (PATCH 제외) | POST /v1/posts 회귀 0, alembic 왕복 |
| 2 | Backend | PATCH /v1/media/{id} + rate_limit + (OQ-D-1=A 시) auction 정책 | 단위 8 테스트 + smoke 5단계 |
| 3 | Frontend | 의존성 설치 + 타입 변경 + DragHandleIcon | tsc 0, draft 호환성 |
| 4 | Frontend | useMediaUploadQueue + SortableMediaCard + MediaUploadProgress + MediaPreviewList 재작성 | dnd-kit 데스크탑 drag, SSR hydration |
| 5 | Frontend | EditorWorkspace/EditorStepContent/page.tsx 호출부 연결 | **5 통합 지점 체크리스트 전체** |
| 6 | Frontend | i18n 5 locale × 11 키 | 5 locale 전환 |
| 7 | Frontend | 회귀 + viewport + a11y + 3G + 키보드 reorder | AC-1~10 전체 Pass |

> Backend Step 1-2 → Frontend Step 3-7 순차. 단 Step 1과 Step 3는 의존성 없음 → 병렬 가능.

---

## 14. 통합 Risks Summary

| 영역 | 가장 큰 위험 | 완화 |
|------|--------------|------|
| Backend | BR-2 OQ-D-1 미결 → auction policy 누락 | Step 2 게이트 |
| Backend | BR-1 alembic downgrade 데이터 손실 | pg_dump 백업 |
| Frontend | R-FE-1 5 통합 지점 회귀 | Step 4·5 직후 체크 |
| Frontend | R-FE-3 구버전 draft 호환성 | optional + fallback |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-01 | Initial draft. Backend + Frontend 두 agent 병렬 작성 → 통합. OQ-D 5개 surface (D-1 backend auction 정책 / D-2 textarea 높이 / D-3 progress 정확도 / D-4 DragOverlay / D-5 OQ-1 echo) | itpe-ince + Claude Opus 4.7 (통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션) |
| 1.1 | 2026-05-02 | OQ-D 5개 모두 Resolved. **OQ-D-3은 사용자 결정으로 권장(A mock)에서 B(XHR 실제 progress 추적)로 변경** — `uploadMediaFile`을 `uploadMediaFileWithProgress`로 리팩토링하여 XHR 기반 실제 progress 추적. 나머지 4개는 권장(A) 채택. §F-5/F-15/F-16 갱신 + 신규 R-FE-8 추가. Do 단계 진입 준비 완료 | itpe-ince (Claude Opus 4.7) |
