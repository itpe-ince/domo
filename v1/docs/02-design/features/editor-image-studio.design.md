---
template: design
version: 1.0
feature: editor-image-studio
sub-pdca: "#6-image"
date: 2026-05-03
author: itpe-ince (Claude Opus 4.7 + bkit:bkend-expert + bkit:frontend-architect agents)
project: domo
project_version: v1
parent_plan: editor-image-studio.plan.md
parent_roadmap: editor-revamp-roadmap.plan.md
sister_pdca: editor-video-studio.plan.md
---

# editor-image-studio Design Document

> **Summary**: 이미지 4기능 에디터(회전·크롭·모자이크·워터마크) — Konva 클라이언트 미리보기 + Pillow 서버 처리 + `crop_meta jsonb` 비파괴 메타 + `POST /v1/media/{id}/transform` 엔드포인트.
>
> **Status**: Draft v1.0
> **Plan v1.1**: [editor-image-studio.plan.md](../../01-plan/features/editor-image-studio.plan.md)
> **Sister**: [editor-video-studio.plan.md](../../01-plan/features/editor-video-studio.plan.md)

---

## 0. OQ Resolution Echo (Plan v1.1 + Design v1.1)

### Plan OQ (v1.1)
| ID | 결정 | 영향 |
|----|------|------|
| OQ-1 = B | Konva + react-konva (4기능 단일) | Frontend |
| OQ-3 = A | crop_meta jsonb 보존 (비파괴) | Backend B-2 + Frontend F-9 |
| OQ-5 = C | 워터마크 텍스트 + 시그니처 둘 다 | Backend §B-6 + Frontend F-8 |
| OQ-7 = A | 데스크탑+모바일 동시 | Frontend F-14 |
| OQ-8 = C | `_check_auction_media_lock` 동일 적용 | Backend §B-7 |
| OQ-9 = B | GIF 편집 비활성 | Backend §B-5 (415) + Frontend F-10 |

### Design OQ-D (v1.1, 2026-05-03 결정)
| ID | 결정 | 영향 |
|----|------|------|
| OQ-D-A = C | `MediaAsset.original_storage_key` 컬럼 추가 (비파괴) | Backend alembic 0038, B-2/B-6 재처리 기반 |
| OQ-D-B = C | `User.signature_storage_key` 사전 저장 (SSRF 회피) | Backend alembic 0038, 신규 §B-14 시그니처 업로드 endpoint |
| OQ-D-C = B | 재처리 기반 = 항상 최초 원본 (OQ-D-A=C 전제) | Backend B-6 process_image_transform |
| OQ-D-1 = A | Konva Stage = 컨테이너 fit + DPR | Frontend F-12 |
| OQ-D-2 = A | 단축키 1/2/3/4 도입 | Frontend F-11 |
| **OQ-D-3 = B** | **별도 시그니처 업로드 UI** (avatar 재사용 ❌) | **Frontend 신규 SignatureUploadButton + Backend §B-14 endpoint 필수** |
| OQ-D-4 | A 시도 (Konva.Filters.Pixelate) → 부족 시 B fallback | Frontend F-7 MosaicTool 구현 시 검증 |
| OQ-D-5 = A | "원본" preset = 크롭 초기화 통합 | Frontend F-6 CropTool |

---

## 1. Goals & Non-Goals

### 1.1 Goals
1. 작가가 별도 도구 없이 플랫폼 내에서 이미지 편집 (회전/크롭/모자이크/워터마크)
2. 비파괴 편집 — `crop_meta` jsonb로 ops 보존, 모달 재진입 시 복원
3. 워터마크로 작품 도용 방지 (텍스트 + 시그니처)
4. 5 통합 지점 회귀 0 + 5 locale 동시 출시
5. 자매 PDCA `editor-video-studio`와 독립 진행 (인프라 의존성 0)

### 1.2 Non-Goals
영상 편집·메이킹 모달(자매 PDCA), 이미지 자동 보정, preset filter, AI 배경 제거, 다중 일괄 편집, GIF 편집, props drilling 개편.

### 1.3 OQ-D-3=B 결정에 따른 추가 Goals (Design v1.1)
- 별도 시그니처 업로드 UI/엔드포인트 신설 (avatar 재사용 ❌)
- `User.signature_storage_key` 사전 저장 → 워터마크 도구는 키만 참조 (SSRF 차단)

---

## 2. Architecture Overview

### 2.1 데이터 흐름

```
[사용자 카드 "편집" 클릭]
   ↓ setEditingMediaId(id)
[ImageEditor 모달 마운트] (dynamic import, Konva lazy)
   ↓ initialOps = media.crop_meta (있으면 복원)
[useImageEditor hook] — rotation/crop/mosaic/watermark state
   ↓ Konva Stage 미리보기 (도구 4종)
[사용자 "저장" 클릭]
   ↓ buildCropMeta() → CropMeta
   ↓ patchMediaTransform(id, {ops})
[POST /v1/media/{id}/transform]
   ↓ 권한 6단계 (auth → 404 → 403 → auction lock → 415/413 → process)
[process_image_transform(bytes, ops)] — Pillow rotate→crop→mosaic→watermark + EXIF strip + 썸네일 3종
   ↓ storage.put(transformed/{media_id}/{ts}.jpg)
[MediaAsset 갱신] — url/thumbnail_url/thumb_*_url/crop_meta + commit
   ↓ MediaAssetOut 응답
[onSave(updated)] → setters.setMedia → formState 변경
   ↓ useDraftAutosave 2s debounce 자동 trigger
[localStorage + 발행 시 POST /v1/posts에 crop_meta 포함]
```

### 2.2 컴포넌트 트리 (Frontend)

```
page.tsx (CreatePostPageInner)
  ├─ EditorWorkspace / EditorStepContent
  │    └─ MediaPreviewList (props +1: onEditMedia)
  │         └─ DndContext > SortableContext
  │              └─ SortableMediaCard × N
  │                   ├─ DragHandle (기존)
  │                   ├─ 미디어 프리뷰 (기존)
  │                   ├─ EditButton (신규, image+!gif 카드만)
  │                   ├─ Remove button
  │                   └─ caption textarea
  └─ ImageEditor 모달 (dynamic import, editingMediaId 있을 때 마운트)
       ├─ Header + 닫기
       ├─ Konva.Stage > Layer
       │    ├─ Konva.Image (원본)
       │    ├─ Konva.Rect × N (모자이크)
       │    ├─ Konva.Text + Konva.Image (워터마크)
       ├─ ToolPanel
       │    ├─ RotateTool / CropTool / MosaicTool / WatermarkTool
       └─ Footer (저장 + 취소 + spinner)
```

### 2.3 Backend 변경 파일 (5개)
- `alembic/versions/0037_media_crop_meta.py` (신규)
- `models/post.py` `MediaAsset.crop_meta` JSONB
- `schemas/post.py` `CropMetaSchema` + `MediaTransformOp` discriminated union + `MediaTransformRequest` + `MediaAssetIn.crop_meta?`
- `api/media.py` `POST /{media_id}/transform`
- `services/media_processing.py` `process_image_transform()`
- `core/rate_limit.py` `media_transform` scope (5/min/user)
- `services/storage/{base,local,s3}.py` `get()` 메서드 추가 (transform 시 원본 읽기 위해)

---

## 백엔드 설계 (B 섹션)

> 출처: `bkit:bkend-expert` agent

### B-1. Backend 변경 개요

본 PDCA 백엔드 작업 범위는 6개 파일에 한정: `alembic/versions/0037_media_crop_meta.py` (신규 마이그레이션), `models/post.py` (`MediaAsset.crop_meta` 컬럼), `schemas/post.py` (`CropMetaSchema` / `MediaTransformOp` / `MediaTransformRequest` / `MediaAssetIn.crop_meta` 추가), `api/media.py` (`POST /v1/media/{media_id}/transform`), `services/media_processing.py` (`process_image_transform()` 신규), `core/rate_limit.py` (`media_transform` 추가). 기존 `PATCH /v1/media/{id}` (caption) 및 업로드 엔드포인트는 변경 없이 유지. 영상은 자매 PDCA 범위.

### B-2. 데이터 모델 — `MediaAsset.crop_meta` + `original_storage_key`

`caption` 컬럼 (#4) 패턴 그대로:

```python
from sqlalchemy.dialects.postgresql import JSONB

# editor-image-studio PDCA #6-image — non-destructive edit metadata.
crop_meta: Mapped[dict | None] = mapped_column(
    JSONB, nullable=True, default=None
)
# OQ-D-A = C — 비파괴 원본 보존. 첫 transform 시 storage_key 복사.
original_storage_key: Mapped[str | None] = mapped_column(
    String(512), nullable=True, default=None
)
```

- `crop_meta`: PostgreSQL JSONB (인덱스 불요 — 검색 대상 아님)
- `original_storage_key`: nullable. 신규 업로드 시 NULL → 첫 transform 시 자동 채움
- nullable + default None — 기존 행 자동 NULL
- 280자 제한 같은 컬럼 제약 없음 — Pydantic schema가 검증

### B-2.1. `original_storage_key` 채움 규칙 (v1.2 추가, F-1 fix)

**목적**: OQ-D-C = B (재처리 = 항상 최초 원본) 보장.

| 시나리오 | 동작 |
|---------|------|
| 신규 업로드 (현재 #4 미디어) | `original_storage_key = NULL` (Pillow 처리 전 단계라 변경 없음) |
| **첫 번째 transform** | endpoint 진입 직후 `if media.original_storage_key is None: media.original_storage_key = media.storage_key` → flush → `provider.get(media.original_storage_key)`로 처리 |
| 두 번째 이후 transform | `provider.get(media.original_storage_key or media.storage_key)` — 항상 최초 원본 기반 |
| 기존 행 backfill | **하지 않음** — NULL 시 코드가 자동 fallback (`original_storage_key or storage_key`). pre-existing 미디어의 첫 transform이 사실상 "첫 원본"으로 기록 |

**구현 위치**: `app/api/media.py::transform_media()` 진입 직후 (auction lock 체크 후, Pillow 처리 전):

```python
# v1.2 — OQ-D-A=C / OQ-D-C=B 일관성 보장
if media.original_storage_key is None:
    media.original_storage_key = media.storage_key
    # SQLAlchemy autoflush가 commit 전 INSERT/UPDATE 처리
source_key = media.original_storage_key  # 항상 최초 원본
original_bytes = await provider.get(source_key)
```

**주의**: backfill alembic을 추가하지 않는 이유 — pre-existing 미디어의 storage_key는 이미 "원본 또는 최신 결과물" 중 하나일 수 있어 자동 backfill이 의미 없음. 사용자가 첫 transform 호출 시점부터 "그 시점의 storage_key"를 원본으로 간주하는 것이 가장 안전.

### B-3. Alembic Migration (`0037_media_crop_meta.py`)

```python
"""Add crop_meta column to media_assets — editor-image-studio PDCA #6-image.

Stores non-destructive image edit metadata (rotate/crop/mosaic/watermark ops)
as JSONB. Enables ImageEditor modal to restore previous edit state on
re-entry (OQ-3 = A — non-destructive editing).

Additive migration — existing rows get crop_meta=NULL automatically.
Downgrade drops the column and irrevocably loses crop metadata.

Revision ID: 0037_media_crop_meta
Revises: 0036_media_caption
Create Date: 2026-05-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0037_media_crop_meta"
down_revision: Union[str, None] = "0036_media_caption"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column(
            "crop_meta",
            JSONB,
            nullable=True,
            comment=(
                "Non-destructive image edit metadata (OQ-3=A). "
                "Stores applied ops (rotate/crop/mosaic/watermark) as JSONB. "
                "NULL for video/external_embed or unedited images."
            ),
        ),
    )


def downgrade() -> None:
    # WARNING: Drops all crop_meta data irreversibly.
    op.drop_column("media_assets", "crop_meta")
```

### B-4. Pydantic Schema

#### CropMetaSchema (직렬화 형태)

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field


class CropRect(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)


class MosaicRegion(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)
    strength: Literal[10, 20, 40] = Field(20)


class WatermarkPosition(BaseModel):
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)


class WatermarkMeta(BaseModel):
    source: Literal["text", "signature"]
    text: str | None = Field(None, max_length=100)
    position: WatermarkPosition
    size: int | None = Field(None, gt=0)
    opacity: float = Field(0.7, ge=0.1, le=1.0)


class CropMetaSchema(BaseModel):
    version: int = Field(1, description="스키마 진화 추적")
    rotation: Literal[0, 90, 180, 270] = Field(0)
    crop: CropRect | None = None
    mosaic_regions: list[MosaicRegion] = Field(default_factory=list)
    watermark: WatermarkMeta | None = None
```

#### MediaTransformOp (Discriminated Union)

```python
class RotateOp(BaseModel):
    type: Literal["rotate"]
    degrees: Literal[90, 180, 270]


class CropOp(BaseModel):
    type: Literal["crop"]
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)
    ratio: str | None = None  # '1:1' | '4:3' | '16:9' | 'original' (참고용)


class MosaicOp(BaseModel):
    type: Literal["mosaic"]
    regions: list[MosaicRegion] = Field(..., min_length=1)


class WatermarkOp(BaseModel):
    type: Literal["watermark"]
    source: Literal["text", "signature"]
    text: str | None = Field(None, max_length=100)
    position: WatermarkPosition
    size: int | None = Field(None, gt=0)
    opacity: float = Field(0.7, ge=0.1, le=1.0)


MediaTransformOp = Annotated[
    Union[RotateOp, CropOp, MosaicOp, WatermarkOp],
    Field(discriminator="type"),
]


class MediaTransformRequest(BaseModel):
    ops: list[MediaTransformOp] = Field(..., min_length=1)
```

#### MediaAssetIn 확장

```python
class MediaAssetIn(BaseModel):
    # ... 기존 필드 ...
    caption: str | None = Field(None, max_length=280)
    crop_meta: CropMetaSchema | None = None  # 신규
```

`MediaAssetOut`은 `MediaAssetIn`을 상속하므로 자동 노출.

### B-5. `POST /v1/media/{media_id}/transform` 엔드포인트

**권한 흐름 6단계**:
1. `get_current_user` → 401
2. `MEDIA_NOT_FOUND` 404
3. `MEDIA_NOT_OWNER` 403 (`post.author_id != user.id`)
4. `_check_auction_media_lock(db, post)` 409 (OQ-8=C, #4 헬퍼 재사용)
5. 입력 검증: `media.type != "image"` → 415 / GIF 확장자 → 415 / `size > 20MB` → 413
6. Pillow transform → 새 파일 저장 → MediaAsset 갱신 → 응답

```python
TRANSFORM_MAX_BYTES = 20 * 1024 * 1024
GIF_EXTENSIONS = {".gif"}


@router.post("/{media_id}/transform")
async def transform_media(
    media_id: uuid.UUID,
    body: MediaTransformRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_transform"),
):
    # 1. 미디어 조회
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if media is None:
        raise ApiError("MEDIA_NOT_FOUND", "Media asset not found", http_status=404)

    # 2. 소유자 검증
    post_result = await db.execute(select(Post).where(Post.id == media.post_id))
    post = post_result.scalar_one_or_none()
    if post is None or post.author_id != user.id:
        raise ApiError("MEDIA_NOT_OWNER", "You can only edit your own media", http_status=403)

    # 3. Auction lock (OQ-8=C, #4 재사용)
    await _check_auction_media_lock(db, post)

    # 4. 타입/형식 검증
    if media.type != "image":
        raise ApiError(
            "MEDIA_TRANSFORM_UNSUPPORTED_TYPE",
            "Transform은 이미지 타입만 지원합니다",
            http_status=415,
        )
    storage_key = media.storage_key or media.url
    if Path(storage_key).suffix.lower() in GIF_EXTENSIONS:
        raise ApiError(
            "MEDIA_TRANSFORM_UNSUPPORTED_TYPE",
            "GIF 이미지 편집은 지원하지 않습니다",
            http_status=415,
        )

    # 5. 크기 검증
    if media.size_bytes and media.size_bytes > TRANSFORM_MAX_BYTES:
        raise ApiError(
            "MEDIA_TRANSFORM_TOO_LARGE",
            f"이미지 크기가 20MB를 초과합니다 ({media.size_bytes // (1024*1024)}MB)",
            http_status=413,
        )

    # 6. 원본 읽기 + Pillow transform
    provider = get_storage_provider()
    original_bytes = await provider.get(media.storage_key)
    try:
        processed = process_image_transform(original_bytes, body.ops)
    except Exception as e:
        _log.error("media.transform.failed: media_id=%s err=%s", media_id, e)
        raise ApiError("MEDIA_TRANSFORM_FAILED", "이미지 처리 중 오류", http_status=500) from e

    # 7. 결과물 저장 (transformed/{media_id}/{timestamp}.jpg)
    normalized_ext = ".jpg" if processed.original_format == "JPEG" else ".png"
    timestamp = int(datetime.now(timezone.utc).timestamp())
    new_key = f"transformed/{media_id}/{timestamp}{normalized_ext}"
    stem = new_key[: -len(normalized_ext)]

    stored = await provider.put(new_key, processed.original, processed.content_type)
    thumb_urls: dict[str, str] = {}
    for size_name, thumb_bytes in processed.thumbs.items():
        thumb_key = f"{stem}_thumb_{size_name}{normalized_ext}"
        thumb_obj = await provider.put(thumb_key, thumb_bytes, processed.content_type)
        thumb_urls[size_name] = thumb_obj.url

    # 8. crop_meta 빌드 (ops에서 최종 상태 추출)
    crop_meta = _build_crop_meta(body.ops)

    # 9. MediaAsset 갱신
    media.url = stored.url
    media.storage_key = stored.key
    media.storage_provider = stored.provider
    media.size_bytes = stored.size_bytes
    media.width = processed.width
    media.height = processed.height
    media.thumbnail_url = thumb_urls.get("small")
    media.thumb_small_url = thumb_urls.get("small")
    media.thumb_medium_url = thumb_urls.get("medium")
    media.thumb_large_url = thumb_urls.get("large")
    media.crop_meta = crop_meta.model_dump() if crop_meta else None

    await db.commit()
    await db.refresh(media)

    # 10. Audit log
    _log.info(
        "media.transform.applied",
        extra={
            "event": "media.transform.applied",
            "user_id": str(user.id),
            "media_id": str(media_id),
            "post_id": str(media.post_id),
            "ops_summary": [op.type for op in body.ops],
            "new_storage_key": new_key,
        },
    )

    return {"data": MediaAssetOut.model_validate(media).model_dump(mode="json")}
```

### B-6. `process_image_transform()` (Pillow)

처리 순서: **rotate → crop → mosaic → watermark** (정규화). EXIF 재제거 + 3 썸네일 재생성 필수.

```python
def process_image_transform(
    image_bytes: bytes,
    ops: list[MediaTransformOp],
) -> ProcessedImage:
    img = Image.open(io.BytesIO(image_bytes))
    img.load()
    img = ImageOps.exif_transpose(img)

    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    out_format = "PNG" if has_alpha else "JPEG"
    content_type = "image/png" if has_alpha else "image/jpeg"

    ops_by_type: dict[str, list] = {k: [] for k in ["rotate", "crop", "mosaic", "watermark"]}
    for op in ops:
        if op.type in ops_by_type:
            ops_by_type[op.type].append(op)

    # rotate (누적)
    for r in ops_by_type["rotate"]:
        img = img.rotate(-r.degrees, expand=True)  # Pillow는 반시계 → 부호 반전

    # crop (마지막만)
    if ops_by_type["crop"]:
        c = ops_by_type["crop"][-1]
        w, h = img.size
        box = (max(0, c.x), max(0, c.y), min(w, c.x + c.w), min(h, c.y + c.h))
        img = img.crop(box)

    # mosaic (각 region에 적용)
    for m in ops_by_type["mosaic"]:
        for region in m.regions:
            img = _apply_mosaic(img, region)

    # watermark (마지막만)
    if ops_by_type["watermark"]:
        img = _apply_watermark(img, ops_by_type["watermark"][-1])

    # EXIF 재제거
    data = list(img.getdata())
    cleaned = Image.new(img.mode, img.size)
    cleaned.putdata(data)

    # 재인코딩 + 썸네일 3종
    original_bytes = _encode(cleaned, out_format)
    thumbs: dict[str, bytes] = {}
    for name, max_side in THUMB_SIZES.items():
        if max(cleaned.size) <= max_side:
            thumbs[name] = original_bytes
            continue
        thumb = cleaned.copy()
        thumb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        thumbs[name] = _encode(thumb, out_format)

    return ProcessedImage(
        original=original_bytes,
        original_format=out_format,
        width=cleaned.size[0],
        height=cleaned.size[1],
        thumbs=thumbs,
        content_type=content_type,
    )


def _apply_mosaic(img: Image.Image, region: MosaicRegion) -> Image.Image:
    x, y, w, h = region.x, region.y, region.w, region.h
    strength = region.strength
    box = (x, y, x + w, y + h)
    region_img = img.crop(box)
    small_w = max(1, w // strength)
    small_h = max(1, h // strength)
    pixelated = region_img.resize((small_w, small_h), Image.Resampling.NEAREST).resize(
        (w, h), Image.Resampling.NEAREST
    )
    img = img.copy()
    img.paste(pixelated, box)
    return img


def _apply_watermark(img: Image.Image, wm_op: WatermarkOp) -> Image.Image:
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    alpha_value = int(wm_op.opacity * 255)

    if wm_op.source == "text" and wm_op.text:
        draw = ImageDraw.Draw(overlay)
        font_size = wm_op.size or 36
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        draw.text(
            (wm_op.position.x, wm_op.position.y),
            wm_op.text,
            fill=(255, 255, 255, alpha_value),
            font=font,
        )
    elif wm_op.source == "signature":
        # OQ-D-3 결정에 따라 _apply_watermark_signature() 호출 (avatar URL fetch or pre-uploaded key)
        pass

    return Image.alpha_composite(base, overlay)
```

### B-7. 권한·정책 (OQ-8=C)

`_check_auction_media_lock()` (#4) 그대로 재사용. transform도 caption과 동일한 차단 로직.

### B-8. Storage 통합

- 결과물 경로: `transformed/{media_id}/{timestamp}.{ext}` + `..._thumb_{small,medium,large}.{ext}`
- **`StorageProvider.get()` 추상 메서드 추가 필요** — `base.py`/`local.py`/`s3.py` 모두 구현
- 원본 파일 보존 정책 — **OQ-D-A로 surface (§14)**

### B-9. Audit Log + Rate Limit

```python
# rate_limit.py
"media_transform": {"limit": 5, "window_sec": 60, "by": "user"},
```

5/min은 `media_patch`(30/min)보다 6배 엄격 — Pillow transform이 CPU 집약적이므로 DDoS 방어.

Audit log: `_log.info("media.transform.applied", extra={...ops_summary, original_storage_key, new_storage_key})`. ops 내용 상세 미기록 (개인정보·로그 크기 보호).

### B-10. Error Codes (10종, v1.2 — signature 4종 추가)

| 코드 | HTTP | 발생 |
|------|------|------|
| `MEDIA_NOT_FOUND` | 404 | (재사용) |
| `MEDIA_NOT_OWNER` | 403 | (재사용) |
| `AUCTION_ACTIVE_MEDIA_LOCKED` | 409 | (재사용) |
| `MEDIA_TRANSFORM_TOO_LARGE` | 413 | size > 20MB |
| `MEDIA_TRANSFORM_UNSUPPORTED_TYPE` | 415 | 비-이미지 또는 GIF |
| `MEDIA_TRANSFORM_FAILED` | 500 | Pillow 처리 오류 (상세 미노출) |
| `WATERMARK_SIGNATURE_NOT_SET` | 400 | watermark.source="signature" 인데 `User.signature_storage_key IS NULL` (frontend i18n 키 `tool.watermark.signature.notSet` 매핑) |
| `SIGNATURE_TOO_LARGE` | 413 | signature 업로드 size > 2MB |
| `SIGNATURE_UNSUPPORTED_TYPE` | 415 | signature MIME 비-(image/png \| image/webp) |
| `SIGNATURE_UPLOAD_FAILED` | 500 | storage put 실패 |

### B-11. Test Strategy (Backend)

단위 테스트 10개 (rotate90/180, crop+클램프, mosaic, watermark text, EXIF strip, 썸네일 3종, op 순서 정규화, 빈 ops). 통합 테스트 7개 (정상/403/404/409/415/429/회귀). Smoke `scripts/smoke_test_image_transform.sh` 5단계 (rotate/crop/mosaic/watermark/GIF 차단 확인).

### B-12. Backend Implementation Order

- **Step 1 (1일)**: alembic 0037 + MediaAsset.crop_meta + Pydantic schemas + rate_limit scope
- **Step 2 (0.5일)**: `process_image_transform()` + `_apply_mosaic` + `_apply_watermark` + 단위 테스트 10개
- **Step 3 (1일)**: `StorageProvider.get()` 추가 + `transform_media` 엔드포인트 + audit log
- **Step 4 (0.5일)**: 통합 테스트 + smoke + 회귀

### B-13. Backend Risks

| Risk | 심각도 | 완화 |
|------|:---:|------|
| Pillow watermark 알파 합성 — JPEG에 RGBA 합성 모드 충돌 | Medium | `convert("RGBA")` 후 `alpha_composite` → JPEG 재인코딩 시 RGB 변환 |
| EXIF 재제거 누락 (워터마크 후 GPS 잔존) | High | 재인코딩 직전 `getdata + Image.new + putdata` 명시적 strip + 단위 테스트 |
| 큰 이미지 메모리 폭증 | Medium | 413 차단 + 업로드 단계 10MB 제한 |
| Storage cleanup 실패 시 partial file 잔존 | Medium | put 루프 try/except + 실패 시 `provider.delete()` 정리 |
| crop_meta 스키마 진화 비용 | Low | `version` 필드 + Pydantic default 1 |
| 워터마크 signature 이미지 SSRF 위험 | Medium | **OQ-D-B = C 채택** — `User.signature_storage_key` 사전 저장, 워터마크 도구는 키만 참조 (외부 fetch ❌) |
| 원본 손실 (재처리 시 재인코딩 누적 손실) | High | **OQ-D-A = C, OQ-D-C = B 채택** — `MediaAsset.original_storage_key` 컬럼 + 항상 최초 원본 기반 재처리 |

### B-14. Signature Upload Endpoint (OQ-D-3=B + OQ-D-B=C 결정)

**OQ-D-3 = B (별도 시그니처 업로드 UI)** + **OQ-D-B = C (사전 저장)** 조합으로, 워터마크 시그니처 업로드 전용 엔드포인트를 신설한다. avatar 재사용 ❌ — 시그니처는 워터마크 전용 자산으로 분리 관리.

#### B-14.1 alembic 0038 (`User.signature_storage_key`)

```python
# v1/backend/alembic/versions/0038_user_signature_storage_key.py
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("signature_storage_key", sa.String(length=512), nullable=True),
    )
    # MediaAsset.original_storage_key (OQ-D-A = C)
    op.add_column(
        "media_assets",
        sa.Column("original_storage_key", sa.String(length=512), nullable=True),
    )
```

> ⚠️ **alembic 0037 (crop_meta) + 0038 (original_storage_key + signature_storage_key) 두 마이그레이션 동시 작성** — 의존성 0이므로 0038은 0037 down_revision.

#### B-14.2 신규 endpoint: `POST /v1/me/signature`

| 항목 | 명세 |
|------|------|
| Path | `POST /v1/me/signature` |
| Auth | `current_active_user` (JWT) |
| Body | `multipart/form-data: file` |
| 검증 | type=image, MIME ∈ {image/png, image/webp}, size ≤ 2MB, 권장 dim ≤ 1024×512 (투명 배경) |
| 처리 | EXIF strip → storage put → `User.signature_storage_key` 갱신 → 기존 키 있으면 cleanup |
| 응답 | `{ "signature_url": "..." }` (presigned 또는 public URL) |
| Rate limit | `signature_upload` 5/min/user |
| Audit log | `signature_upload`, user_id, prev_key, new_key |
| Error codes | `SIGNATURE_TOO_LARGE` (413), `SIGNATURE_UNSUPPORTED_TYPE` (415), `SIGNATURE_UPLOAD_FAILED` (500) |

#### B-14.3 신규 endpoint: `DELETE /v1/me/signature`

| 항목 | 명세 |
|------|------|
| Path | `DELETE /v1/me/signature` |
| 처리 | storage delete → `signature_storage_key = NULL` → audit log |
| 응답 | `204 No Content` |

#### B-14.4 신규 endpoint: `GET /v1/me/signature`

| 항목 | 명세 |
|------|------|
| Path | `GET /v1/me/signature` |
| 응답 | `{ "signature_url": "..." | null }` (없으면 null, 워터마크 도구가 사용 가능 여부 판단) |

#### B-14.5 워터마크 처리 변경

`process_image_transform()`의 `WatermarkOp` 처리 시:
- 사용자가 시그니처 워터마크 선택 → `User.signature_storage_key` 조회 → 없으면 `WATERMARK_SIGNATURE_NOT_SET` (400) → 있으면 storage에서 직접 GET (외부 URL fetch ❌, SSRF 차단)
- `WatermarkOp.source` discriminated union: `"text"` | `"signature"` (URL 필드 제거 — 항상 사전 저장 키 사용)

#### B-14.6 Backend Implementation Order 갱신

- **Step 1 (1.5일)**: alembic 0037 + 0038 + MediaAsset.crop_meta + MediaAsset.original_storage_key + User.signature_storage_key + Pydantic schemas + rate_limit (`media_transform`, `signature_upload`)
- **Step 2 (0.5일)**: `process_image_transform()` + `_apply_mosaic` + `_apply_watermark` + 단위 테스트 10개 (signature 처리 포함)
- **Step 3 (1.5일)**: `StorageProvider.get()` + `transform_media` endpoint + signature 3 endpoints (POST/GET/DELETE) + audit log
- **Step 4 (0.5일)**: 통합 테스트 + smoke + 회귀

---

## 프런트엔드 설계 (F 섹션)

> 출처: `bkit:frontend-architect` agent

### F-1. Frontend 변경 개요

세 축: (1) `konva@^9` + `react-konva@^18` 도입 (프로젝트 두 번째 외부 React lib, 첫 번째는 #4 `@dnd-kit/*`). (2) `SortableMediaCard.tsx`에 `EditButton` 진입점 추가 — `media.type === "image" && !gif`. (3) `ImageEditor` 모달 — Konva Stage + 4 도구 + 비파괴 재진입 + transform API. `crop_meta` 옵션 필드로 `DraftState` 자연 통합 (#4 caption 패턴), `useDraftAutosave` 코드 변경 0.

### F-2. 의존성 도입

```json
{
  "dependencies": {
    "@dnd-kit/core": "^6.3.1",
    "@dnd-kit/sortable": "^8.0.0",
    "konva": "^9.3.16",
    "react-konva": "^18.2.10",
    ...
  }
}
```

번들 크기 추정: konva ~40KB + react-konva ~10KB = **~50KB gzip**. 임계 80KB. 초과 시 `dynamic({ ssr: false })` lazy import.

React 19 호환성: 본 PDCA는 React 18 — 즉각 위험 없음. SSR: Konva는 client-only, `dynamic({ ssr: false })` lazy import 기본 권장 (Step 2 시작 직후 최소 샘플 검증).

### F-3. 컴포넌트 트리 (반복 — §2.2 참조)

### F-4. 신규 컴포넌트 카탈로그

| 컴포넌트 | 위치 | 책임 |
|---|---|---|
| `ImageEditor` | `post-editor/studio/ImageEditor.tsx` | 모달 + Konva Stage + 4 도구 조율 + transform API 호출 |
| `RotateTool` | `post-editor/studio/tools/RotateTool.tsx` | 90°/180°/270° 누적 회전 |
| `CropTool` | `post-editor/studio/tools/CropTool.tsx` | Konva Transformer + preset 5종 |
| `MosaicTool` | `post-editor/studio/tools/MosaicTool.tsx` | 드래그 영역 추가 + 픽셀 강도 |
| `WatermarkTool` | `post-editor/studio/tools/WatermarkTool.tsx` | 텍스트 + 시그니처 + 5 preset 위치 + 자유 드래그 |
| `EditButton` (inline) | `SortableMediaCard.tsx` 내부 | image+!gif 카드만, hover/focus 시 표시 |
| `EditIcon` 등 5종 | `icons.tsx` | 도구 아이콘 |

각 컴포넌트 props 인터페이스 — frontend agent 본문 §F-4 참조 (ImageEditorProps / RotateToolProps / CropToolProps / MosaicToolProps / WatermarkToolProps).

### F-5. 신규 Hook — `useImageEditor`

`lib/hooks/useImageEditor.ts`:

```ts
interface ImageEditorState {
  rotation: 0 | 90 | 180 | 270;
  cropRect: CropRect | null;
  cropPreset: CropPreset;  // 'free' | '1:1' | '4:3' | '16:9' | 'original'
  mosaicRegions: MosaicRegion[];
  mosaicPixelSize: 10 | 20 | 40;
  watermark: WatermarkConfig;
  saving: boolean;
  saveError: string | null;
  showOriginal: boolean;
}

function useImageEditor(media: CreatePostMedia, initialOps?: CropMeta): {
  state: ImageEditorState;
  stageRef: React.RefObject<Konva.Stage>;
  setRotation, setCropRect, setCropPreset, addMosaicRegion, removeMosaicRegion,
  setMosaicPixelSize, setWatermark, toggleShowOriginal,
  handleSave: () => Promise<CreatePostMedia | null>,
  buildCropMeta: () => CropMeta,
}
```

마운트 1회 `useEffect`에서 `initialOps`를 각 setter로 풀어 복원 (비파괴 재진입).

### F-6. 데이터 모델 (Frontend types)

#### CropMeta (api.ts) — 백엔드 jsonb 1:1 대응

```ts
export interface CropMeta {
  version: 1;
  rotate_deg: 0 | 90 | 180 | 270;
  crop?: { x: number; y: number; width: number; height: number };  // 0.0~1.0
  mosaic_regions: { x, y, width, height, pixel_size: 10 | 20 | 40 }[];
  watermark?: {
    text?: string;
    text_enabled: boolean;
    signature_enabled: boolean;
    position: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right' | 'center' | 'custom';
    custom_x?: number;
    custom_y?: number;
    font_size?: number;
    opacity?: number;
  };
}
```

#### CreatePostMedia 확장

```ts
export type CreatePostMedia = {
  // ... 기존 ...
  caption?: string;
  _clientId?: string;
  crop_meta?: CropMeta;  // 신규
};
```

#### `patchMediaTransform()` API client

```ts
export async function patchMediaTransform(
  mediaId: string,
  body: MediaTransformRequest
): Promise<MediaTransformResponse> {
  return apiFetch<MediaTransformResponse>(
    `/media/${encodeURIComponent(mediaId)}/transform`,
    { method: "POST", body: JSON.stringify(body) }
  );
}
```

DraftState 자동 통합 — `useDraftAutosave.ts` 코드 변경 0.

### F-7. ImageEditor 모달 UX

- 데스크탑 ≥ md: `max-w-4xl max-h-[90vh]` centered + `bg-black/70 backdrop-blur-sm`
- 모바일 < md: `inset-0` full-screen
- Focus trap (LoginModal/DraftRestoreDialog 패턴) + ESC → onCancel
- 저장 시: `saving=true` + `pointer-events-none` + `aria-busy` → API 호출 → 성공 시 `onSave(updated)` + 모달 닫음 / 실패 시 `saveError` Footer 표시 (특히 409 "경매 진행 중 편집 불가")
- Konva Stage 크기: ResizeObserver + DPR 보정 (`Stage.width = container × dpr, scaleX = dpr, CSS = container`)

### F-8. 4 도구 UX

#### RotateTool
3 버튼 — 클릭 시 `rotation = (rotation + n) % 360`. Konva Image `rotation={state.rotation}` + `offsetX={width/2}, offsetY={height/2}` 중앙 회전.

#### CropTool
Konva `Transformer` + Image 노드 + `boundBoxFunc`로 Stage 경계 클램프. 비율 preset 4종 + free + original. `onTransformEnd` 시 Stage 좌표 → 0.0~1.0 비율 정규화.

#### MosaicTool
Stage `onMouseDown/Move/Up` 드래그 영역 → MosaicRegion 추가. Konva `Rect` with pixelated fill (Konva.Filters.Pixelate 우선, 없으면 커스텀 — OQ-D-4). 영역 선택 후 Delete 키로 제거. 강도 슬라이더 (10/20/40).

#### WatermarkTool (OQ-D-3 = B 결정 반영)
- 텍스트 input → Konva Text 노드
- 시그니처 토글 → **신규 `SignatureUploadButton`** (`GET /v1/me/signature` 결과 기반)
  - signature_url 존재 → 토글 활성화 + Konva Image로 미리보기
  - signature_url null → 토글 비활성 + "시그니처 업로드" 버튼 노출 → `SignatureUploadModal` 오픈
  - 업로드 완료 시 `useSignature` hook이 `mutate()` → 토글 자동 활성화
  - "시그니처 변경" / "시그니처 삭제" 버튼 (DELETE 호출)
- 5 preset 버튼 (top_left/top_right/bottom_left/bottom_right/center) → 위치 즉시 이동
- `draggable={true}` → 자유 드래그 → `position="custom"` + `custom_x/y` 비율 저장
- 백엔드 `WatermarkOp.source = "signature"` → 백엔드는 `User.signature_storage_key`에서 직접 GET (URL 필드 미사용)

### F-9. 비파괴 편집 + 재진입 (OQ-3=A)

```ts
useEffect(() => {  // 마운트 1회
  if (!initialOps) return;
  if (initialOps.rotate_deg !== undefined) setRotation(initialOps.rotate_deg);
  if (initialOps.crop) {
    setCropRect(initialOps.crop);
    setCropPreset(inferPreset(initialOps.crop));
  }
  if (initialOps.mosaic_regions?.length) setMosaicRegions(initialOps.mosaic_regions);
  if (initialOps.watermark) setWatermark(backendWatermarkToConfig(initialOps.watermark));
}, []);
```

저장 흐름: `buildCropMeta()` → `patchMediaTransform()` → `onSave({...media, url, thumbnail_url, crop_meta})` → `setters.setMedia` → `formState` 변경 → `useDraftAutosave` 2s debounce 자동 trigger.

취소: formState 미수정.

### F-10. SortableMediaCard 편집 버튼

```ts
const isGif = (url: string) => /\.gif(\?|$)/i.test(url);
const showEditButton = media.type === "image" && !isGif(media.url);
```

GIF 카드: 편집 버튼 완전 미표시 (OQ-9=B).

위치: Remove 버튼 옆 `top-1 right-1 flex gap-1`. 모바일: 항상 표시 (`opacity-100 md:opacity-0 md:group-hover:opacity-100`).

`SortableMediaCard` props 추가:
```ts
onEditMedia: (id: string) => void;
```

`MediaPreviewList` → `SortableMediaCard` props pass-through.

`page.tsx`:
```tsx
{editingMediaId && targetMedia && (
  <ImageEditor
    media={targetMedia}
    initialOps={targetMedia.crop_meta}
    onSave={(updated) => {
      setters.setMedia(prev => prev.map(m => m._clientId === updated._clientId ? updated : m));
      setEditingMediaId(null);
    }}
    onCancel={() => setEditingMediaId(null)}
  />
)}
```

### F-10b. Signature Upload UI (OQ-D-3 = B + OQ-D-B = C 신규)

#### 신규 컴포넌트
- `v1/frontend/src/components/post-editor/SignatureUploadModal.tsx` — multipart `POST /v1/me/signature` 호출 모달
- `v1/frontend/src/components/post-editor/SignaturePreview.tsx` — 현재 시그니처 미리보기 + 변경/삭제 버튼

#### 신규 hook
```ts
// v1/frontend/src/lib/hooks/useSignature.ts
export function useSignature() {
  const [signatureUrl, setSignatureUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // GET /v1/me/signature on mount
  // upload(file): POST → setSignatureUrl
  // remove(): DELETE → setSignatureUrl(null)
  return { signatureUrl, loading, upload, remove };
}
```

#### 신규 API client (`api.ts`)
```ts
export async function getMySignature(): Promise<{ signature_url: string | null }> { ... }
export async function uploadMySignature(file: File): Promise<{ signature_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch("/users/me/signature", { method: "POST", body: formData });
}
export async function deleteMySignature(): Promise<void> { ... }
```

#### UX 흐름 (WatermarkTool 안)
1. 모달 첫 마운트 시 `useSignature()` hook이 `GET /v1/me/signature` 호출
2. `signature_url` 있음 → 시그니처 토글 활성, 미리보기 + "변경"/"삭제" 버튼
3. `signature_url` null → 토글 비활성 + "시그니처 업로드" CTA 버튼 → `SignatureUploadModal` 오픈
4. SignatureUploadModal: 파일 선택(.png/.webp 권장) → 업로드 → 성공 시 부모 ImageEditor 모달의 시그니처 토글 자동 활성화
5. 검증 (Frontend): 2MB 초과 시 즉시 reject + i18n 토스트 (`tool.watermark.signature.tooLarge`)
6. 백엔드 응답 처리: `SIGNATURE_TOO_LARGE`(413) / `SIGNATURE_UNSUPPORTED_TYPE`(415) → i18n 매핑

#### i18n 신규 키 (~10개)
- `tool.watermark.signature.{upload, change, remove, uploading, currentSignature, supportedFormats, tooLarge, unsupportedType, removeConfirm}`
- `tool.watermark.signature.modal.{title, fileInput, hint}`

> **5 locale × 10 키 = 50 entries 추가** (기존 170 + 신규 50 = 총 220 entries)

#### 회귀 영향
- 5 통합 지점 회귀 0 유지 (signature는 워터마크 도구 내부 캡슐화)
- props drilling 영향 없음 (`useSignature` hook 자체 호출, page.tsx → ImageEditor → WatermarkTool 라인에 추가 props 0)

### F-11. i18n Keys (`post.editor.media.studio.image.*`)

**~34 키 × 5 locale = 170 entries**:

- `editor.{title, save, saving, cancel, preview.toggle}` (5)
- `tool.rotate.{label, 90, 180, 270}` (4)
- `tool.crop.{label, free, 1_1, 4_3, 16_9, original}` (6)
- `tool.mosaic.{label, strength.{10,20,40}, clear}` (5)
- `tool.watermark.{label, text.placeholder, signature.toggle, position.{topLeft,topRight,bottomLeft,bottomRight,center}}` (8)
- `error.{tooLarge, unsupportedType, auctionLocked, failed}` (4)
- `editButton.{aria, gifDisabled}` (2)

ICU 보간 없음 (단순 문자열).

### F-12. Accessibility

- 모달 `role="dialog" aria-modal="true" aria-labelledby="image-editor-title"`
- Focus trap (Tab/Shift+Tab 순환) + ESC → onCancel
- 모든 도구 버튼 `aria-label`
- Konva Stage `tabIndex={0} role="img" aria-label="이미지 편집 캔버스"`
- prefers-reduced-motion: 모달 fade-in 비활성. Konva 자체에 CSS transition 없음
- 저장 중 `aria-disabled="true" aria-busy="true"`
- 도구 단축키 1/2/3/4 (OQ-D-2=A 권장)

### F-13. Performance

- Konva Stage 4096px 이상 입력 → Image.onload에서 리사이즈 후 Stage 로드 (메모리 보호)
- `dynamic({ ssr: false })` lazy import — Konva 초기 번들 분리
- 도구 컴포넌트 `React.memo` + `useCallback` setters
- 모자이크: `Konva.Filters.Pixelate` 우선 (OQ-D-4)

### F-14. Mobile UX (OQ-7=A)

- 모달 `inset-0` full-screen
- ToolPanel **bottom sheet**: `fixed bottom-0 w-full bg-surface border-t rounded-t-xl max-h-[40vh] overflow-y-auto`
- Konva touch 이벤트 네이티브 지원
- Transformer 핸들 `anchorSize={20}` 이상 (WCAG 44px 터치 타겟)

### F-15. Test Strategy (Frontend)

수동 검증.

**5 통합 지점 회귀** — Step 1 직후 + Step 4 직후 두 번 전체 실행:
1. useDraftAutosave: caption 입력 + crop_meta 변경 → 2s 후 localStorage 모두 포함
2. DraftRestoreDialog: 재진입 시 crop_meta 복원 + 모달 재오픈 → ops 복원
3. 멀티탭 storage event
4. PostTypeSelector role-gating
5. useArtistGate

**이미지 에디터 동작**: 4 도구 + GIF 차단 + 비파괴 재진입 + auction 409 + ESC 취소 + Konva 키보드 이벤트 충돌 없음.

**Viewport** 4종 (375/768/1024/1280) + **5 locale** (ko/en/ja/zh/es).

### F-16. Frontend Implementation Order

- **Step 1 (1일)**: 의존성 + 타입(api.ts) + 5 아이콘 + EditButton 진입점 + props pass-through
- **Step 2 (1일)**: ImageEditor 모달 골격 + Konva Stage + dynamic lazy import + SSR 검증
- **Step 3 (3일)**: 4 도구 (RotateTool → CropTool → MosaicTool → WatermarkTool) + PreviewToggleButton
- **Step 4 (1일)**: useImageEditor 비파괴 재진입 + transform API 통합 + 5 통합 지점 회귀 체크
- **Step 5 (0.5일)**: 5 locale i18n × 34 키
- **Step 6 (0.5일)**: 회귀 + viewport + a11y + 409 메시지

### F-17. Frontend Risks

| ID | 리스크 | 영향 | 대응 |
|----|--------|:---:|------|
| R-FE-1 | 5 통합 지점 회귀 | High | Step 1 + Step 4 두 번 체크 |
| R-FE-2 | Konva + Next.js 15 SSR | High | `dynamic({ ssr: false })` 기본. Step 2 직후 검증 |
| R-FE-3 | 큰 이미지 Konva 메모리 | Medium | 4096px 리사이즈 + 백엔드 413 |
| R-FE-4 | 모바일 touch 정확도 | Medium | `anchorSize={20}` + 실기기 |
| R-FE-5 | crop_meta 스키마 진화 | Medium | version 필드 + graceful degradation |
| R-FE-6 | 모자이크 렌더 품질 | Low | Konva.Filters.Pixelate 우선 |
| R-FE-7 | EditorWorkspace props ~44 | Low | 본 PDCA 유지 |
| R-FE-8 | Konva lazy load 첫 오픈 지연 | Low | spinner 표시 |

---

## 11. New Open Questions for Design Phase (OQ-D) — ✅ ALL RESOLVED (v1.1)

Backend agent + Frontend agent 합산 8개 모두 결정됨 (2026-05-03):

| ID | 영역 | 질문 | 결정 |
|---|---|---|:---:|
| **OQ-D-A** | Backend | 원본 파일 보존 정책 | ✅ **C** — `MediaAsset.original_storage_key` 컬럼 추가 (alembic 0038) |
| **OQ-D-B** | Backend | 워터마크 시그니처 취득 방법 | ✅ **C** — `User.signature_storage_key` 사전 저장 (SSRF 차단) |
| **OQ-D-C** | Backend | 재처리 기반 | ✅ **B** — 항상 최초 원본 (OQ-D-A=C 전제, 누적 손실 0) |
| **OQ-D-1** | Frontend | Konva Stage 크기 정책 | ✅ **A** — 컨테이너 fit + DPR 보정 |
| **OQ-D-2** | Frontend | 도구 전환 단축키 (1/2/3/4) | ✅ **A 도입** |
| **OQ-D-3** | F+B | 워터마크 시그니처 소스 | ✅ **B** — **별도 업로드 UI** (avatar 재사용 ❌). 신규 §B-14 endpoint 3종 + Frontend §F-10b SignatureUploadModal |
| **OQ-D-4** | Frontend | 모자이크 미리보기 렌더 | ✅ **A 시도 → B fallback** — `Konva.Filters.Pixelate` 우선, 부족 시 Canvas 2D |
| **OQ-D-5** | Frontend | 크롭 초기화 | ✅ **A** — "원본" preset 통합 |

> OQ-D-3 = B 결정으로 **alembic 0038에 `signature_storage_key` 추가** + **시그니처 업로드 모달 신설**. 작업량 +1.5일 (Backend +1일 / Frontend +0.5일).

---

## 12. Test Strategy 통합

| 영역 | 검증 |
|------|------|
| Backend 단위 | 12개 (Pillow ops + EXIF + 썸네일 + signature 처리 2개) |
| Backend 통합 | 10개 (transform 7 + signature upload/get/delete 3) |
| Backend Smoke | `smoke_test_image_transform.sh` 5단계 + `smoke_test_signature.sh` 3단계 |
| Frontend 5 통합 지점 | Step 1 + Step 4 두 번 |
| Frontend 4 도구 | 회전/크롭/모자이크/워터마크 + 비파괴 재진입 |
| Frontend SignatureUploadModal | 업로드/변경/삭제 + 413/415 에러 매핑 |
| Frontend Viewport | 375/768/1024/1280 |
| Frontend 5 locale | ko/en/ja/zh/es |
| End-to-end | (a) 시그니처 업로드 → (b) 카드 편집 클릭 → 4 도구 → 저장 → DB crop_meta 저장 + 새 url + 발행 → (c) 발행 후 modal 재진입 → ops 복원 → 시그니처 워터마크 정상 적용 |

---

## 13. Implementation Order 통합 (Design v1.1 — OQ-D-3=B 추가 반영)

| Step | 영역 | 작업 |
|------|------|------|
| 1 | Backend | alembic 0037 (`crop_meta`) + 0038 (`original_storage_key` + `signature_storage_key`) + MediaAsset/User 모델 + Pydantic schemas + rate_limit (`media_transform`, `signature_upload`) |
| 2 | Backend | `process_image_transform()` + `_apply_mosaic` + `_apply_watermark` (signature는 `User.signature_storage_key`에서 직접 GET) + 단위 테스트 12개 |
| 3 | Backend | `StorageProvider.get()` + `transform_media` endpoint + signature 3 endpoints (POST/GET/DELETE `/v1/me/signature`) + audit log |
| 4 | Backend | 통합 테스트 (transform 7 + signature 3) + smoke 2종 + 회귀 |
| 5 | Frontend | 의존성(konva, react-konva) + 타입(`CropMeta`, `WatermarkOp.source` discriminated union) + 아이콘 + EditButton 진입점 |
| 6 | Frontend | ImageEditor 모달 골격 + Konva Stage + lazy import + SSR 검증 |
| 7 | Frontend | 4 도구 구현 (RotateTool/CropTool/MosaicTool/WatermarkTool) |
| 7b | Frontend | **신규** SignatureUploadModal + SignaturePreview + `useSignature` hook + `getMySignature/uploadMySignature/deleteMySignature` API client |
| 8 | Frontend | useImageEditor 비파괴 재진입 + `patchMediaTransform` API + 5 통합 지점 회귀 |
| 9 | Frontend | 5 locale i18n × 44 키 (기본 34 + 시그니처 신규 10) = 220 entries |
| 10 | Frontend | 회귀 + viewport + a11y |

Step 1-4 (Backend, ~4일 — 0038 추가로 +1일) + Step 5-10 (Frontend, ~7.5일 — Step 7b 추가로 +0.5일) = **총 11.5일 (M~L 5-8일 plan보다 큼, OQ-D-3=B 영향)**. Backend Step 1과 Frontend Step 5는 의존성 0이라 병렬 가능 → 단축 9.5일 가능.

> ⚠️ **가장 큰 시간 비용**: Step 7b SignatureUploadModal — 시그니처 업로드 단독 동작 검증 + 14개 i18n 키 + 3개 API endpoint 통합. MVP 후속 또는 alembic만 0038 함께 깔고 UI는 Phase 2로 빼는 옵션도 가능 (사용자 결정 필요 — 본 v1.1에서는 같이 진행 가정).

---

## 14. Risks Summary

가장 큰 위험: **OQ-D-A/B/C 미결 시 워터마크 signature + 재처리 기반 구현 불가**. Step 2 시작 전 결정 필수.

| 영역 | 핵심 위험 | 완화 |
|------|-----------|------|
| Backend | OQ-D-A/B/C 미결 | Step 2 게이트 |
| Backend | EXIF 재제거 누락 | 명시적 strip + 단위 테스트 |
| Backend | SSRF (시그니처 fetch) | OQ-D-B=C로 회피 |
| Frontend | R-FE-1 5 통합 지점 회귀 | Step 1 + Step 4 두 번 체크 |
| Frontend | R-FE-2 SSR hydration | dynamic lazy import + Step 6 검증 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-05-03 | Initial draft. Backend (bkit:bkend-expert) + Frontend (bkit:frontend-architect) 두 agent 병렬 작성 → 통합. OQ-D 8개 surface (A/B/C backend + 1/2/3/4/5 frontend, OQ-D-3 통합). Konva + Pillow + crop_meta jsonb + transform endpoint + 비파괴 편집 흐름 완전 명세 | itpe-ince + Claude Opus 4.7 (통합) + bkit:bkend-expert (B 섹션) + bkit:frontend-architect (F 섹션) |
| 1.1 | 2026-05-03 | OQ-D 8개 결정 반영. **OQ-D-3 = B 채택** (별도 시그니처 업로드 UI/엔드포인트, avatar 재사용 ❌). 신규 §B-14 시그니처 업로드 endpoint 3종 (POST/GET/DELETE `/v1/me/signature`) + alembic 0038 (`original_storage_key` + `signature_storage_key`) + Frontend §F-10b SignatureUploadModal + `useSignature` hook + Step 7b 추가. i18n 키 34→44 (총 220 entries). 추정 10일 → 11.5일 (단축 9.5일). 나머지 7개 OQ-D는 권장값 채택 (A=C, B=C, C=B, 1=A, 2=A, 4=A시도, 5=A) | itpe-ince + Claude Opus 4.7 |
| 1.2 | 2026-05-03 | bkit:design-validator 피드백 반영. F-1 fix: §B-2.1 신규 — `original_storage_key` 채움 규칙 (첫 transform 시 자동 복사, backfill 미시행) 명세. F-2 fix: §B-10 error code 4종 추가 (`WATERMARK_SIGNATURE_NOT_SET` 400 + `SIGNATURE_TOO_LARGE` 413 + `SIGNATURE_UNSUPPORTED_TYPE` 415 + `SIGNATURE_UPLOAD_FAILED` 500). | itpe-ince + Claude Opus 4.7 + bkit:design-validator |
| 1.3 | 2026-05-03 | Backend Step 1 구현 시 발견 — alembic revision ID 길이 제약 (`alembic_version.version_num` = `varchar(32)`). 0038 revision을 `0038_signature_and_original_storage` (35자, 한도 초과) → `0038_orig_signature_keys` (24자)로 단축. 향후 모든 0039+ migration은 ≤32자 권장. | itpe-ince |
| 1.4 | 2026-05-03 | Backend Step 3 구현 시 path 정합성 결정 — 기존 프로젝트는 `/v1/me` 라우터 (`api/me.py`)에 자기 자원 endpoint를 통합하는 패턴. design v1.3의 `/v1/users/me/signature` 3종 → `/v1/me/signature` 3종으로 통일 (별도 `users/me` prefix 미신설). Backend `me.py`에 `POST/GET/DELETE /signature` 추가. Frontend `useSignature` hook + `SignatureUploadModal` 모두 `/v1/me/signature` 사용. §B-14.2/3/4 + §F-10b + §13 Step 1-3 모두 path 일괄 갱신. | itpe-ince + bkit:bkend-expert |
