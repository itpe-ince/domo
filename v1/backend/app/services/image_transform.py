"""Image transform pipeline for editor-image-studio PDCA #6-image (Backend Step 2).

Pure, sync, I/O-free image processing. No DB, no storage, no FastAPI.
Called by the Step 3 endpoint after loading bytes from storage.

Normalized op order: rotate → crop → mosaic → watermark.
EXIF re-stripped after all ops. 3 thumbnails regenerated.

Reference: design §B-6 (core implementation), §B-13 (risks), §B-14.5 (signature).
"""
from __future__ import annotations

import io
import logging
from functools import reduce

from PIL import Image, ImageDraw, ImageFont

from app.schemas.media_transform import (
    CropMetaSchema,
    CropOp,
    CropRect,
    MediaTransformOp,
    MosaicOp,
    MosaicRegion,
    RotateOp,
    WatermarkMeta,
    WatermarkOp,
    WatermarkPosition,
)
from app.services.media_processing import (
    THUMB_SIZES,
    ProcessedImage,
    _encode,
    _strip_exif_and_orient,
)

log = logging.getLogger(__name__)

# ----- Custom exceptions -------------------------------------------------------


class WatermarkSignatureNotSetError(Exception):
    """Raised when WatermarkOp.source == 'signature' but signature_bytes is None.

    The Step 3 endpoint maps this to WATERMARK_SIGNATURE_NOT_SET (HTTP 400).
    """


# ----- Internal op normalisation ----------------------------------------------


def _normalize_ops(
    ops: list[MediaTransformOp],
) -> tuple[RotateOp | None, CropOp | None, MosaicOp | None, WatermarkOp | None]:
    """Sort / deduplicate ops into canonical order.

    Rules:
    - Multiple RotateOps: sum degrees mod 360 (0 → discard).
    - Multiple CropOps: last one wins.
    - Multiple MosaicOps: collapse all `.regions` lists into a single MosaicOp.
    - Multiple WatermarkOps: last one wins.
    """
    rotates = [op for op in ops if isinstance(op, RotateOp)]
    crops = [op for op in ops if isinstance(op, CropOp)]
    mosaics = [op for op in ops if isinstance(op, MosaicOp)]
    watermarks = [op for op in ops if isinstance(op, WatermarkOp)]

    # Rotate: sum, mod 360; None if net 0.
    rotate_out: RotateOp | None = None
    if rotates:
        total = reduce(lambda acc, r: acc + r.degrees, rotates, 0) % 360
        if total != 0:
            rotate_out = RotateOp(type="rotate", degrees=total)  # type: ignore[arg-type]

    # Crop: last wins.
    crop_out: CropOp | None = crops[-1] if crops else None

    # Mosaic: merge all regions.
    mosaic_out: MosaicOp | None = None
    if mosaics:
        all_regions: list[MosaicRegion] = []
        for m in mosaics:
            all_regions.extend(m.regions)
        mosaic_out = MosaicOp(type="mosaic", regions=all_regions)

    # Watermark: last wins.
    watermark_out: WatermarkOp | None = watermarks[-1] if watermarks else None

    return rotate_out, crop_out, mosaic_out, watermark_out


# ----- Individual op applicators ----------------------------------------------


def _apply_rotate(img: Image.Image, op: RotateOp) -> Image.Image:
    """Rotate clockwise by op.degrees.

    For multiples of 90 use lossless transpose; arbitrary degrees fall back
    to `img.rotate` (expand=True).
    """
    d = op.degrees % 360
    if d == 90:
        return img.transpose(Image.Transpose.ROTATE_270)  # PIL CCW → CW
    if d == 180:
        return img.transpose(Image.Transpose.ROTATE_180)
    if d == 270:
        return img.transpose(Image.Transpose.ROTATE_90)
    # Generic fallback (not reached given Literal[90,180,270] schema)
    return img.rotate(-d, expand=True)


def _apply_crop(img: Image.Image, op: CropOp) -> Image.Image:
    """Crop, clamping to image bounds to prevent blank borders or exceptions."""
    w, h = img.size
    x = max(0, min(op.x, w - 1))
    y = max(0, min(op.y, h - 1))
    cw = min(op.w, w - x)
    ch = min(op.h, h - y)
    if cw <= 0 or ch <= 0:
        return img  # degenerate rect → no-op
    return img.crop((x, y, x + cw, y + ch))


def _apply_mosaic_region(img: Image.Image, region: MosaicRegion) -> Image.Image:
    """Pixelate a single region using NEAREST downscale + upscale."""
    iw, ih = img.size
    x = max(0, min(region.x, iw - 1))
    y = max(0, min(region.y, ih - 1))
    rw = min(region.w, iw - x)
    rh = min(region.h, ih - y)
    if rw <= 0 or rh <= 0:
        return img

    strength = region.strength
    small_w = max(1, rw // strength)
    small_h = max(1, rh // strength)

    box = (x, y, x + rw, y + rh)
    patch = img.crop(box)
    pixelated = patch.resize((small_w, small_h), Image.Resampling.NEAREST).resize(
        (rw, rh), Image.Resampling.NEAREST
    )
    out = img.copy()
    out.paste(pixelated, (x, y))
    return out


def _apply_mosaic(img: Image.Image, op: MosaicOp) -> Image.Image:
    for region in op.regions:
        img = _apply_mosaic_region(img, region)
    return img


def _apply_watermark(
    img: Image.Image,
    op: WatermarkOp,
    signature_bytes: bytes | None,
) -> Image.Image:
    """Composite watermark onto image.

    Always converts to RGBA for alpha_composite, then converts back to RGB
    if the downstream format is JPEG (handled by _encode).

    B-13 risk: RGBA → JPEG mode conflict avoided here; _encode handles final
    RGB conversion.
    """
    base = img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    alpha_value = int(op.opacity * 255)

    if op.source == "text":
        if op.text:
            draw = ImageDraw.Draw(overlay)
            font_size = op.size or 24
            try:
                font = ImageFont.load_default(size=font_size)
            except TypeError:
                # Older Pillow without size param
                font = ImageFont.load_default()
            draw.text(
                (op.position.x, op.position.y),
                op.text,
                fill=(255, 255, 255, alpha_value),
                font=font,
            )
        composited = Image.alpha_composite(base, overlay)

    elif op.source == "signature":
        if signature_bytes is None:
            raise WatermarkSignatureNotSetError(
                "WatermarkOp.source='signature' but no signature_bytes provided. "
                "Endpoint maps this to WATERMARK_SIGNATURE_NOT_SET (400)."
            )
        try:
            sig_img = Image.open(io.BytesIO(signature_bytes)).convert("RGBA")
        except Exception as exc:
            raise ValueError(f"Cannot decode signature image: {exc}") from exc

        # Resize signature to op.size (treated as max width in pixels)
        if op.size and sig_img.width > op.size:
            ratio = op.size / sig_img.width
            new_size = (op.size, max(1, int(sig_img.height * ratio)))
            sig_img = sig_img.resize(new_size, Image.Resampling.LANCZOS)

        # Apply opacity to alpha channel
        if alpha_value < 255:
            r, g, b, a = sig_img.split()
            a = a.point(lambda v: int(v * op.opacity))
            sig_img = Image.merge("RGBA", (r, g, b, a))

        # Paste onto overlay at specified position (clamp to base size)
        px = max(0, op.position.x)
        py = max(0, op.position.y)
        overlay.paste(sig_img, (px, py), sig_img)
        composited = Image.alpha_composite(base, overlay)

    else:
        composited = base  # unknown source → no-op

    return composited


# ----- CropMetaSchema builder -------------------------------------------------


def _build_crop_meta(
    rotate_op: RotateOp | None,
    crop_op: CropOp | None,
    mosaic_op: MosaicOp | None,
    watermark_op: WatermarkOp | None,
) -> CropMetaSchema:
    """Build CropMetaSchema from the normalized ops for JSONB persistence."""
    rotation_val: int = 0
    if rotate_op is not None:
        rotation_val = rotate_op.degrees % 360

    crop_rect: CropRect | None = None
    if crop_op is not None:
        crop_rect = CropRect(x=crop_op.x, y=crop_op.y, w=crop_op.w, h=crop_op.h)

    mosaic_regions: list[MosaicRegion] = []
    if mosaic_op is not None:
        mosaic_regions = list(mosaic_op.regions)

    watermark_meta: WatermarkMeta | None = None
    if watermark_op is not None:
        watermark_meta = WatermarkMeta(
            source=watermark_op.source,
            text=watermark_op.text,
            position=WatermarkPosition(
                x=watermark_op.position.x,
                y=watermark_op.position.y,
            ),
            size=watermark_op.size,
            opacity=watermark_op.opacity,
        )

    # CropMetaSchema.rotation is Literal[0,90,180,270]; rotation_val is already
    # constrained by RotateOp.degrees Literal + mod 360.
    return CropMetaSchema(
        version=1,
        rotation=rotation_val,  # type: ignore[arg-type]
        crop=crop_rect,
        mosaic_regions=mosaic_regions,
        watermark=watermark_meta,
    )


# ----- Public API -------------------------------------------------------------


def process_image_transform(
    image_bytes: bytes,
    ops: list[MediaTransformOp],
    signature_bytes: bytes | None = None,
) -> tuple[ProcessedImage, CropMetaSchema]:
    """Apply transform ops in normalized order, re-strip EXIF, regenerate thumbs.

    Returns (ProcessedImage, CropMetaSchema).
    - ProcessedImage: caller (Step 3 endpoint) persists bytes to storage.
    - CropMetaSchema: caller persists as JSONB in MediaAsset.crop_meta.

    Sync + pure — no I/O, no DB. Unit-testable with in-memory bytes.

    Normalized op order: rotate → crop → mosaic → watermark (design §B-6).

    Args:
        image_bytes: Raw image bytes (caller loads from original_storage_key).
        ops: Transform ops; applied in normalized order regardless of input order.
        signature_bytes: Required if any WatermarkOp has source="signature".
            Endpoint loads from User.signature_storage_key. If None and a
            signature watermark is requested, raises WatermarkSignatureNotSetError.

    Raises:
        WatermarkSignatureNotSetError: signature watermark requested but no bytes.
        ValueError: Unreadable image_bytes.
    """
    # --- Load + initial EXIF orient ---
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    # Decide output format once (alpha → PNG, else JPEG)
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    out_format = "PNG" if has_alpha else "JPEG"
    content_type = "image/png" if has_alpha else "image/jpeg"

    # Initial EXIF strip + orient
    img = _strip_exif_and_orient(img)

    # --- Normalize ops ---
    rotate_op, crop_op, mosaic_op, watermark_op = _normalize_ops(ops)

    # --- Apply in canonical order ---
    if rotate_op is not None:
        img = _apply_rotate(img, rotate_op)

    if crop_op is not None:
        img = _apply_crop(img, crop_op)

    if mosaic_op is not None:
        img = _apply_mosaic(img, mosaic_op)

    if watermark_op is not None:
        img = _apply_watermark(img, watermark_op, signature_bytes)

    # --- Re-strip EXIF (B-13: guard against signature EXIF leaking back) ---
    # _strip_exif_and_orient rebuilds from pixel data, discarding all metadata.
    # _apply_watermark may return RGBA; _strip_exif_and_orient handles any mode.
    img = _strip_exif_and_orient(img)

    # After watermark the image may be RGBA; update out_format
    if img.mode in ("RGBA", "LA"):
        out_format = "PNG"
        content_type = "image/png"

    # --- Encode original ---
    original_bytes = _encode(img, out_format)

    # --- Generate 3 thumbnails ---
    thumbs: dict[str, bytes] = {}
    for name, max_side in THUMB_SIZES.items():
        if max(img.size) <= max_side:
            thumbs[name] = original_bytes
            continue
        thumb = img.copy()
        thumb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        thumbs[name] = _encode(thumb, out_format)

    processed = ProcessedImage(
        original=original_bytes,
        original_format=out_format,
        width=img.size[0],
        height=img.size[1],
        thumbs=thumbs,
        content_type=content_type,
    )

    # --- Build CropMetaSchema ---
    crop_meta = _build_crop_meta(rotate_op, crop_op, mosaic_op, watermark_op)

    return processed, crop_meta
