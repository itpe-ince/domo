"""Image processing pipeline (Phase 4 M4).

Reference: phase4.design.md §5.5

Responsibilities:
- Strip EXIF metadata (privacy — e.g. GPS coordinates)
- Generate 3 thumbnail sizes: small(400), medium(800), large(1600)
- Re-encode to JPEG with quality=85 (or PNG for transparent)
- Return bytes for each variant

All processing is synchronous (Pillow). For heavy videos this would
be offloaded to a worker; for prototype images this is fast enough.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image, ImageOps

log = logging.getLogger(__name__)

THUMB_SIZES = {
    "small": 400,
    "medium": 800,
    "large": 1600,
}

JPEG_QUALITY = 85


@dataclass
class ProcessedImage:
    original: bytes
    original_format: str      # 'JPEG' | 'PNG'
    width: int
    height: int
    thumbs: dict[str, bytes]  # {'small': bytes, 'medium': bytes, 'large': bytes}
    content_type: str


def _strip_exif_and_orient(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation and strip metadata."""
    # Respect EXIF orientation (portrait photos from phones)
    img = ImageOps.exif_transpose(img)

    # Strip EXIF by recreating with only pixel data
    data = list(img.getdata())
    cleaned = Image.new(img.mode, img.size)
    cleaned.putdata(data)
    return cleaned


def _encode(img: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG":
        # Convert RGBA/P → RGB for JPEG
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (26, 20, 16))  # 두쫀쿠 background
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    else:  # PNG (preserve transparency)
        img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def process_image(raw: bytes) -> ProcessedImage:
    """Process an uploaded image: strip EXIF, generate thumbnails."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:
        raise ValueError(f"Invalid image: {e}") from e

    # Decide output format: preserve transparency, else JPEG
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    out_format = "PNG" if has_alpha else "JPEG"
    content_type = "image/png" if has_alpha else "image/jpeg"

    # Clean + orient original
    cleaned = _strip_exif_and_orient(img)
    original_bytes = _encode(cleaned, out_format)

    # Generate thumbnails
    thumbs: dict[str, bytes] = {}
    for name, max_side in THUMB_SIZES.items():
        # Skip upscaling
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


def image_extension(content_type: str) -> str:
    if content_type == "image/png":
        return ".png"
    return ".jpg"
