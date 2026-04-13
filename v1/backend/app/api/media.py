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

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.services.media_processing import (
    image_extension,
    process_image,
)
from app.services.storage import get_storage_provider
from app.services.storage.local import UPLOAD_ROOT

router = APIRouter(prefix="/media", tags=["media"])

IMAGE_MAX = 10 * 1024 * 1024  # 10 MB
VIDEO_MAX = 50 * 1024 * 1024  # 50 MB
MAKING_VIDEO_MAX = 1024 * 1024 * 1024  # 1 GB

ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v"}


class ExternalEmbedRequest(BaseModel):
    url: str
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
