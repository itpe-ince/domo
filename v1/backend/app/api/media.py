"""Media upload API (Phase 3 Week 14, refactored in Phase 4 M4).

Reference:
- design.md §3.2 POST /media/upload, /media/external
- phase4.design.md §5 StorageProvider

Changes in Phase 4 M4:
- All writes go through StorageProvider (local or s3 via factory)
- Image uploads are processed with Pillow (EXIF strip + 3 thumbnail sizes)
- media_assets columns track storage_provider + storage_key + thumb URLs
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.auction import Auction
from app.models.post import MediaAsset, Post
from app.models.user import User
from app.schemas.media_transform import (
    MediaTransformRequest,
    MediaTransformResponse,
    WatermarkOp,
)
from app.schemas.post import MediaAssetOut, MediaPatchRequest
from app.services.image_transform import (
    WatermarkSignatureNotSetError,
    process_image_transform,
)
from app.services.media_processing import (
    image_extension,
    process_image,
)
from app.services.storage import get_storage_provider
from app.services.storage.local import UPLOAD_ROOT

router = APIRouter(prefix="/media", tags=["media"])

IMAGE_MAX = 10 * 1024 * 1024  # 10 MB
VIDEO_MAX = 200 * 1024 * 1024  # 200 MB
MAKING_VIDEO_MAX = 1024 * 1024 * 1024  # 1 GB

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


class ExternalEmbedRequest(BaseModel):
    url: str
    is_making_video: bool = False


class PresignRequest(BaseModel):
    filename: str
    content_type: str
    is_making_video: bool = False


class FinalizeRequest(BaseModel):
    key: str
    content_type: str
    is_making_video: bool = False


def _ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _classify_kind(ext: str) -> str:
    if ext in ALLOWED_IMAGE_EXT:
        return "image"
    if ext in ALLOWED_VIDEO_EXT:
        return "video"
    return "unknown"


def _build_key(user_id: uuid.UUID, ext: str) -> str:
    today = datetime.now(timezone.utc)
    return f"uploads/{today:%Y/%m}/{user_id}/{uuid.uuid4().hex}{ext}"


def _parse_external(url: str) -> tuple[str, str] | None:
    """Returns (source, external_id) or None."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [None])[0]
        if vid:
            return "youtube", vid
    if "youtu.be" in host:
        vid = parsed.path.lstrip("/")
        if vid:
            return "youtube", vid
    if "vimeo.com" in host:
        m = re.search(r"/(\d+)", parsed.path)
        if m:
            return "vimeo", m.group(1)
    return None


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    is_making_video: bool = Form(False),
    user: User = Depends(get_current_user),
    _rl=rate_limit("media_upload"),
):
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    ext = _ext(file.filename or "")
    kind = _classify_kind(ext)
    if kind == "unknown":
        raise ApiError(
            "VALIDATION_ERROR",
            f"Unsupported file extension: {ext}",
            http_status=422,
        )

    # Determine size limit
    if kind == "image":
        max_bytes = IMAGE_MAX
    elif is_making_video:
        max_bytes = MAKING_VIDEO_MAX
    else:
        max_bytes = VIDEO_MAX

    # Read into memory up to max_bytes + 1 (reject if larger)
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ApiError(
            "VALIDATION_ERROR",
            f"File too large (max {max_bytes // (1024 * 1024)} MB)",
            http_status=422,
        )

    provider = get_storage_provider()

    # Image: process with Pillow + generate thumbnails
    if kind == "image":
        try:
            processed = process_image(data)
        except ValueError as e:
            raise ApiError(
                "VALIDATION_ERROR", f"Image processing failed: {e}", http_status=422
            ) from e

        normalized_ext = image_extension(processed.content_type)
        base_key = _build_key(user.id, normalized_ext)
        stem = base_key[: -len(normalized_ext)]

        # Store original
        original_obj = await provider.put(
            base_key, processed.original, processed.content_type
        )

        # Store thumbnails
        thumb_urls: dict[str, str] = {}
        for size_name, thumb_bytes in processed.thumbs.items():
            thumb_key = f"{stem}_thumb_{size_name}{normalized_ext}"
            thumb_obj = await provider.put(
                thumb_key, thumb_bytes, processed.content_type
            )
            thumb_urls[size_name] = thumb_obj.url

        return {
            "data": {
                "type": "image",
                "url": original_obj.url,
                "thumbnail_url": thumb_urls.get("small"),
                "thumb_small_url": thumb_urls.get("small"),
                "thumb_medium_url": thumb_urls.get("medium"),
                "thumb_large_url": thumb_urls.get("large"),
                "size_bytes": original_obj.size_bytes,
                "width": processed.width,
                "height": processed.height,
                "storage_provider": original_obj.provider,
                "storage_key": original_obj.key,
                "is_making_video": False,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
        }

    # Video: store raw
    key = _build_key(user.id, ext)
    content_type = file.content_type or "application/octet-stream"
    stored = await provider.put(key, data, content_type)

    return {
        "data": {
            "type": "video",
            "url": stored.url,
            "thumbnail_url": None,
            "thumb_small_url": None,
            "thumb_medium_url": None,
            "thumb_large_url": None,
            "size_bytes": stored.size_bytes,
            "storage_provider": stored.provider,
            "storage_key": stored.key,
            "is_making_video": is_making_video,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.post("/presign")
async def presign_upload(
    body: PresignRequest,
    user: User = Depends(get_current_user),
    _rl=rate_limit("media_upload"),
):
    """Return presigned POST credentials for direct S3 upload (phase4.design §5.3).

    Client POSTs the file directly to the returned ``url`` using the ``fields``
    as form data, then calls POST /media/finalize with the ``key`` to register
    the MediaAsset row.
    """
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    ext = _ext(body.filename)
    kind = _classify_kind(ext)
    if kind == "unknown":
        raise ApiError(
            "VALIDATION_ERROR",
            f"Unsupported file extension: {ext}",
            http_status=422,
        )

    if kind == "image":
        max_bytes = IMAGE_MAX
    elif body.is_making_video:
        max_bytes = MAKING_VIDEO_MAX
    else:
        max_bytes = VIDEO_MAX

    key = _build_key(user.id, ext)
    provider = get_storage_provider()
    presigned = await provider.presign_post(
        key=key,
        content_type=body.content_type,
        max_size_bytes=max_bytes,
    )
    return {
        "data": {
            "url": presigned.url,
            "fields": presigned.fields,
            "key": presigned.key,
        }
    }


@router.post("/finalize")
async def finalize_upload(
    body: FinalizeRequest,
    user: User = Depends(get_current_user),
):
    """Register a MediaAsset after a successful presigned POST upload.

    Validates the file exists in storage (provider.exists), then returns
    the public URL so the client can store it on the post/artwork record.
    """
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    provider = get_storage_provider()
    if not await provider.exists(body.key):
        raise ApiError(
            "NOT_FOUND",
            "Upload not found in storage. Ensure the presigned POST completed successfully.",
            http_status=404,
        )

    url = provider.public_url(body.key)
    ext = Path(body.key).suffix.lower()
    kind = _classify_kind(ext)

    return {
        "data": {
            "key": body.key,
            "url": url,
            "type": kind,
            "content_type": body.content_type,
            "is_making_video": body.is_making_video,
        }
    }


@router.post("/external")
async def register_external(
    body: ExternalEmbedRequest,
    user: User = Depends(get_current_user),
):
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    parsed = _parse_external(body.url)
    if not parsed:
        raise ApiError(
            "VALIDATION_ERROR",
            "URL must be a YouTube or Vimeo link",
            http_status=422,
        )
    source, external_id = parsed

    return {
        "data": {
            "type": "external_embed",
            "url": body.url,
            "external_source": source,
            "external_id": external_id,
            "is_making_video": body.is_making_video,
        }
    }


# ─── oEmbed ──────────────────────────────────────────────────────────────

_OEMBED_PROVIDERS = {
    "youtube": {
        "patterns": [r"youtube\.com/watch", r"youtu\.be/"],
        "endpoint": "https://www.youtube.com/oembed?url={url}&format=json",
    },
    "tiktok": {
        "patterns": [r"tiktok\.com/@.+/video/"],
        "endpoint": "https://www.tiktok.com/oembed?url={url}",
    },
    "x": {
        "patterns": [r"(x|twitter)\.com/.+/status/"],
        "endpoint": "https://publish.twitter.com/oembed?url={url}",
    },
    "instagram": {
        "patterns": [r"instagram\.com/(p|reel)/"],
        "endpoint": None,  # Requires Graph API token; fallback to meta tags
    },
}


@router.get("/oembed")
async def get_oembed(
    url: str = Query(..., min_length=5),
):
    """Fetch oEmbed metadata for supported platforms."""
    provider_name = None
    for name, cfg in _OEMBED_PROVIDERS.items():
        for pattern in cfg["patterns"]:
            if re.search(pattern, url):
                provider_name = name
                break
        if provider_name:
            break

    if not provider_name:
        raise ApiError(
            "UNSUPPORTED_URL",
            "Supported: YouTube, TikTok, X(Twitter), Instagram",
            http_status=422,
        )

    provider = _OEMBED_PROVIDERS[provider_name]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if provider["endpoint"]:
                resp = await client.get(provider["endpoint"].format(url=url))
                resp.raise_for_status()
                data = resp.json()
                return {
                    "data": {
                        "provider": provider_name,
                        "title": data.get("title", ""),
                        "thumbnail_url": data.get("thumbnail_url"),
                        "author_name": data.get("author_name"),
                        "url": url,
                    }
                }
            else:
                # Fallback: parse og: meta tags
                resp = await client.get(url, follow_redirects=True)
                html = resp.text[:10000]
                og_title = _extract_meta(html, "og:title") or url
                og_image = _extract_meta(html, "og:image")
                og_author = _extract_meta(html, "og:site_name")
                return {
                    "data": {
                        "provider": provider_name,
                        "title": og_title,
                        "thumbnail_url": og_image,
                        "author_name": og_author,
                        "url": url,
                    }
                }
    except (httpx.HTTPError, Exception):
        # Fallback link card
        return {
            "data": {
                "provider": provider_name,
                "title": url,
                "thumbnail_url": None,
                "author_name": None,
                "url": url,
            }
        }


def _extract_meta(html: str, property_name: str) -> str | None:
    pattern = rf'<meta[^>]+property="{property_name}"[^>]+content="([^"]*)"'
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        return match.group(1)
    pattern2 = rf'<meta[^>]+content="([^"]*)"[^>]+property="{property_name}"'
    match2 = re.search(pattern2, html, re.IGNORECASE)
    return match2.group(1) if match2 else None


@router.get("/files/{key:path}")
async def serve_file(key: str):
    """Serve local-storage files.

    Only active when STORAGE_PROVIDER=local. For s3, the CDN URL
    serves files directly and this route is unused.
    """
    # Path traversal guard
    if ".." in Path(key).parts:
        raise ApiError("NOT_FOUND", "Not found", http_status=404)
    path = UPLOAD_ROOT / key
    if not path.exists() or not path.is_file():
        raise ApiError("NOT_FOUND", "File not found", http_status=404)
    return FileResponse(path)


# ─── editor-media-ux PDCA #4 — Caption editing ─────────────────────────────

_log = logging.getLogger(__name__)


async def _check_auction_media_lock(db: AsyncSession, post: Post) -> None:
    """OQ-D-1 = A — block caption edits while a product post has an active auction.

    Caption changes during an active auction would invalidate bids placed on the
    earlier description. We allow edits before the auction starts and after it
    ends (any non-active status: scheduled / ended / cancelled / settled).

    General posts (post.type='general') and product posts without an active
    auction (no auction row, or auction.status != 'active') are unaffected.
    """
    if post.type != "product":
        return
    result = await db.execute(
        select(Auction).where(
            Auction.product_post_id == post.id,
            Auction.status == "active",
        )
    )
    active_auction = result.scalar_one_or_none()
    if active_auction is not None:
        raise ApiError(
            "AUCTION_ACTIVE_MEDIA_LOCKED",
            "미디어 수정은 경매 종료 후 가능합니다",
            details={"auction_id": str(active_auction.id)},
            http_status=409,
        )


@router.patch("/{media_id}")
async def patch_media(
    media_id: uuid.UUID,
    body: MediaPatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_patch"),
):
    """Update editable fields of a media asset (currently caption only).

    Permission model (OQ-6 = A): only the post author can edit. Edits are
    allowed after publication; the only block is OQ-D-1 = A — active auctions
    lock the caption to protect bidders' decision basis.

    Errors:
      - 404 MEDIA_NOT_FOUND     — media_id does not exist
      - 403 MEDIA_NOT_OWNER     — caller is not the post author
      - 409 AUCTION_ACTIVE_MEDIA_LOCKED — active auction blocks edits (OQ-D-1)
      - 422 (Pydantic)          — caption length > 280
    """
    # 1. Fetch media
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if media is None:
        raise ApiError("MEDIA_NOT_FOUND", "Media asset not found", http_status=404)

    # 2. Authorize via post.author_id (OWASP A01 — Broken Access Control)
    post_result = await db.execute(select(Post).where(Post.id == media.post_id))
    post = post_result.scalar_one_or_none()
    if post is None or post.author_id != user.id:
        raise ApiError(
            "MEDIA_NOT_OWNER",
            "You can only edit your own media",
            http_status=403,
        )

    # 3. Auction lock check (OQ-D-1 = A)
    await _check_auction_media_lock(db, post)

    # 4. Apply update (caption=None is a valid clear operation)
    before_len = len(media.caption) if media.caption else 0
    media.caption = body.caption
    after_len = len(body.caption) if body.caption else 0

    await db.commit()
    await db.refresh(media)

    # 5. Structured audit log — UserActivityLog is a recommendation-engine
    #    model and not appropriate for caption-edit audit; using stdlib
    #    logging keeps the audit trail in the regular log pipeline.
    _log.info(
        "media.caption.updated",
        extra={
            "event": "media.caption.updated",
            "user_id": str(user.id),
            "media_id": str(media.id),
            "post_id": str(media.post_id),
            "caption_before_len": before_len,
            "caption_after_len": after_len,
        },
    )

    return {"data": MediaAssetOut.model_validate(media).model_dump(mode="json")}


# ─── Transform ───────────────────────────────────────────────────────────

TRANSFORM_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
GIF_EXTENSIONS = {".gif"}


@router.post("/{media_id}/transform")
async def transform_media(
    media_id: uuid.UUID,
    body: MediaTransformRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("media_transform"),
):
    """Apply non-destructive image edits and persist crop_meta + new files.

    Permission flow (design §B-5, six steps):
    1. get_current_user (401)
    2. media_assets row → MEDIA_NOT_FOUND (404)
    3. post.author_id != user.id → MEDIA_NOT_OWNER (403)
    4. _check_auction_media_lock(db, post) → AUCTION_ACTIVE_MEDIA_LOCKED (409)
    5. media.type != "image" or .gif → MEDIA_TRANSFORM_UNSUPPORTED_TYPE (415)
       size > 20MB → MEDIA_TRANSFORM_TOO_LARGE (413)
    6. Process via image_transform.py → store new files → update DB → respond

    Errors:
      - 404 MEDIA_NOT_FOUND
      - 403 MEDIA_NOT_OWNER / ACCOUNT_SUSPENDED
      - 409 AUCTION_ACTIVE_MEDIA_LOCKED
      - 415 MEDIA_TRANSFORM_UNSUPPORTED_TYPE
      - 413 MEDIA_TRANSFORM_TOO_LARGE
      - 400 WATERMARK_SIGNATURE_NOT_SET
      - 500 MEDIA_TRANSFORM_FAILED
    """
    # Step 1: account suspended check (mirror upload_media)
    if user.warning_count >= 3 or user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    # Step 2: fetch media
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if media is None:
        raise ApiError("MEDIA_NOT_FOUND", "Media asset not found", http_status=404)

    # Step 3: authorize via post.author_id
    post_result = await db.execute(select(Post).where(Post.id == media.post_id))
    post = post_result.scalar_one_or_none()
    if post is None or post.author_id != user.id:
        raise ApiError(
            "MEDIA_NOT_OWNER",
            "You can only edit your own media",
            http_status=403,
        )

    # Step 4: auction lock (OQ-8=C, reuse #4 helper)
    await _check_auction_media_lock(db, post)

    # Step 5a: type check
    if media.type != "image":
        raise ApiError(
            "MEDIA_TRANSFORM_UNSUPPORTED_TYPE",
            "Transform은 이미지 타입만 지원합니다",
            http_status=415,
        )
    # GIF check (design §B-5 step 4 — use storage_key, not url, for extension)
    storage_key_for_ext = media.storage_key or media.url or ""
    if Path(storage_key_for_ext).suffix.lower() in GIF_EXTENSIONS:
        raise ApiError(
            "MEDIA_TRANSFORM_UNSUPPORTED_TYPE",
            "GIF 이미지 편집은 지원하지 않습니다",
            http_status=415,
        )

    # Step 5b: size check (use DB-recorded size; actual byte check after load)
    if media.size_bytes and media.size_bytes > TRANSFORM_MAX_BYTES:
        raise ApiError(
            "MEDIA_TRANSFORM_TOO_LARGE",
            f"이미지 크기가 20MB를 초과합니다 ({media.size_bytes // (1024 * 1024)}MB)",
            http_status=413,
        )

    # Step 6: load original bytes
    provider = get_storage_provider()

    # §B-2.1 — original_storage_key 채움 (first transform)
    if media.original_storage_key is None:
        media.original_storage_key = media.storage_key
        # SQLAlchemy autoflush will propagate before provider.get query below
    source_key = media.original_storage_key  # always re-process from original (OQ-D-C=B)

    image_bytes = await provider.get(source_key)

    # Double-check actual size after load (handles pre-existing rows without size_bytes)
    if len(image_bytes) > TRANSFORM_MAX_BYTES:
        raise ApiError(
            "MEDIA_TRANSFORM_TOO_LARGE",
            f"이미지 크기가 20MB를 초과합니다 ({len(image_bytes) // (1024 * 1024)}MB)",
            http_status=413,
        )

    # Load signature bytes if any watermark op uses source="signature"
    signature_bytes: bytes | None = None
    needs_sig = any(
        isinstance(op, WatermarkOp) and op.source == "signature"
        for op in body.ops
    )
    if needs_sig:
        if not user.signature_storage_key:
            raise ApiError(
                "WATERMARK_SIGNATURE_NOT_SET",
                "워터마크 시그니처를 먼저 업로드하세요",
                http_status=400,
            )
        signature_bytes = await provider.get(user.signature_storage_key)

    # Call Step 2's pure function
    try:
        processed, crop_meta = process_image_transform(image_bytes, body.ops, signature_bytes)
    except WatermarkSignatureNotSetError as e:
        raise ApiError(
            "WATERMARK_SIGNATURE_NOT_SET",
            "워터마크 시그니처를 먼저 업로드하세요",
            http_status=400,
        ) from e
    except Exception as e:
        _log.exception(
            "media.transform.failed",
            extra={"media_id": str(media_id)},
        )
        raise ApiError("MEDIA_TRANSFORM_FAILED", "이미지 처리 중 오류", http_status=500) from e

    # Generate new storage key for transformed result
    normalized_ext = image_extension(processed.content_type)
    new_key = f"transformed/{media_id}/{uuid.uuid4().hex}{normalized_ext}"
    stem = new_key[: -len(normalized_ext)]

    # Store new files first (before DB update or old-file cleanup)
    new_puts: list[str] = []
    try:
        main_obj = await provider.put(new_key, processed.original, processed.content_type)
        new_puts.append(main_obj.key)

        thumb_urls: dict[str, str] = {}
        for size_name, thumb_bytes in processed.thumbs.items():
            thumb_key = f"{stem}_thumb_{size_name}{normalized_ext}"
            thumb_obj = await provider.put(thumb_key, thumb_bytes, processed.content_type)
            thumb_urls[size_name] = thumb_obj.url
            new_puts.append(thumb_obj.key)
    except Exception as e:
        # Cleanup any partial new puts, then re-raise
        for k in new_puts:
            try:
                await provider.delete(k)
            except Exception:
                _log.warning("transform.new_put_cleanup_failed", extra={"key": k})
        _log.exception("media.transform.storage_put_failed", extra={"media_id": str(media_id)})
        raise ApiError("MEDIA_TRANSFORM_FAILED", "이미지 저장 중 오류", http_status=500) from e

    # Track old keys for cleanup AFTER commit (do NOT delete original_storage_key)
    prev_storage_key = media.storage_key

    # Update DB
    media.storage_provider = main_obj.provider
    media.storage_key = main_obj.key
    media.url = main_obj.url
    media.thumbnail_url = thumb_urls.get("small")
    media.thumb_small_url = thumb_urls.get("small")
    media.thumb_medium_url = thumb_urls.get("medium")
    media.thumb_large_url = thumb_urls.get("large")
    media.width = processed.width
    media.height = processed.height
    media.size_bytes = main_obj.size_bytes
    media.crop_meta = crop_meta.model_dump()  # Pydantic → dict for JSONB
    # original_storage_key already set above (idempotent)

    await db.commit()
    await db.refresh(media)

    # Cleanup old storage files AFTER successful commit
    # Never delete original_storage_key — preserved for re-edits (OQ-D-A=C)
    old_keys_to_clean: list[str] = []
    if prev_storage_key and prev_storage_key != media.original_storage_key:
        old_keys_to_clean.append(prev_storage_key)
        # Best-effort cleanup of old thumbnail keys (derive from stem)
        old_ext = Path(prev_storage_key).suffix.lower()
        old_stem = prev_storage_key[: -len(old_ext)] if old_ext else prev_storage_key
        for size_name in ("small", "medium", "large"):
            old_keys_to_clean.append(f"{old_stem}_thumb_{size_name}{old_ext}")

    for k in old_keys_to_clean:
        try:
            await provider.delete(k)
        except Exception:
            _log.warning("transform.old_file_cleanup_failed", extra={"key": k})

    # Build ops_summary for audit log (counts per type, no op contents)
    ops_type_counts: dict[str, int] = {}
    for op in body.ops:
        ops_type_counts[op.type] = ops_type_counts.get(op.type, 0) + 1

    _log.info(
        "media.transform.applied",
        extra={
            "event": "media.transform.applied",
            "user_id": str(user.id),
            "media_id": str(media_id),
            "post_id": str(media.post_id),
            "ops_summary": ops_type_counts,
            "original_storage_key": media.original_storage_key,
            "new_storage_key": media.storage_key,
            "prev_storage_key": prev_storage_key,
        },
    )

    response_data = MediaTransformResponse(
        id=str(media.id),
        url=media.url,
        thumbnail_url=media.thumbnail_url,
        thumb_small_url=media.thumb_small_url,
        thumb_medium_url=media.thumb_medium_url,
        thumb_large_url=media.thumb_large_url,
        width=media.width,
        height=media.height,
        crop_meta=crop_meta,
    )
    return {"data": response_data.model_dump(mode="json")}
