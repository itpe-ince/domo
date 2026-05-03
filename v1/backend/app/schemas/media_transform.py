"""Pydantic schemas for editor-image-studio PDCA #6-image.

Two model groups:

1. CropMetaSchema (+ children) — serialized form persisted in
   media_assets.crop_meta JSONB. Used to restore the ImageEditor modal
   state on re-entry (OQ-3 = A — non-destructive editing).

2. MediaTransformRequest (+ MediaTransformOp discriminated union) —
   request body for POST /v1/media/{media_id}/transform. Each op describes
   one transform step; the backend applies them in normalized order
   (rotate -> crop -> mosaic -> watermark) and re-encodes from the original.

Both groups share the regions/positions sub-models.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


# -- Sub-models (shared by CropMetaSchema and MediaTransformOp) ---------------


class CropRect(BaseModel):
    """Pixel-space crop rectangle.

    Coordinates are in source-image pixels (post-rotate). Validators ensure
    non-negative offsets and positive dimensions; backend additionally clamps
    against the rotated image bounds.
    """

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
    """Watermark spec persisted in crop_meta.

    `source = "signature"` causes the backend to load the user's
    signature_storage_key (OQ-D-B = C, OQ-D-3 = B) — no external URL fetch.
    """

    source: Literal["text", "signature"]
    text: str | None = Field(None, max_length=100)
    position: WatermarkPosition
    size: int | None = Field(None, gt=0)
    opacity: float = Field(0.7, ge=0.1, le=1.0)


# -- Persisted form: CropMetaSchema ------------------------------------------


class CropMetaSchema(BaseModel):
    """Stored in media_assets.crop_meta (JSONB).

    `version` allows future schema evolution without migration. The
    ImageEditor modal reads this to restore op state on re-entry.
    """

    version: int = Field(1, description="Schema evolution tracking")
    rotation: Literal[0, 90, 180, 270] = Field(0)
    crop: CropRect | None = None
    mosaic_regions: list[MosaicRegion] = Field(default_factory=list)
    watermark: WatermarkMeta | None = None


# -- Request form: MediaTransformOp discriminated union ----------------------


class RotateOp(BaseModel):
    type: Literal["rotate"]
    degrees: Literal[90, 180, 270]


class CropOp(BaseModel):
    type: Literal["crop"]
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    w: int = Field(..., gt=0)
    h: int = Field(..., gt=0)
    # Informational tag for the frontend preset that produced these dims
    # ('1:1' | '4:3' | '16:9' | 'free' | 'original'). Not used by backend.
    ratio: str | None = None


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
    """POST /v1/media/{media_id}/transform request body.

    Empty ops list is rejected (`min_length=1`); the endpoint applies
    operations in a normalized order regardless of input order.
    """

    ops: list[MediaTransformOp] = Field(..., min_length=1)


class MediaTransformResponse(BaseModel):
    """POST /v1/media/{media_id}/transform response."""

    id: str
    url: str
    thumbnail_url: str | None = None
    thumb_small_url: str | None = None
    thumb_medium_url: str | None = None
    thumb_large_url: str | None = None
    width: int | None = None
    height: int | None = None
    crop_meta: CropMetaSchema


# -- Signature upload (OQ-D-3 = B, OQ-D-B = C) -------------------------------


class SignatureResponse(BaseModel):
    """GET /v1/users/me/signature and POST /v1/users/me/signature responses.

    `signature_url` is null when the user has not uploaded a signature.
    """

    signature_url: str | None = None
