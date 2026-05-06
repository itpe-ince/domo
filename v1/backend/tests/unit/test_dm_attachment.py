"""DM 첨부파일 단위 테스트 — Phase 9 L-C (L-7 File Attachment).

presign URL 발급, MIME 검증, 크기 제한 검증.
1:1 DM presign 엔드포인트를 직접 테스트.

테스트 케이스:
  1. 허용 MIME 목록 검증 — 5종 모두 허용
  2. 금지 MIME → 422
  3. 10MB 이하 파일 → 허용
  4. 10MB 초과 파일 → 422
  5. presign 응답 구조 확인 (upload_url, key, expires_in)
  6. 경계값: 정확히 10MB → 허용
  7. 파일명 특수문자 포함 → 정상 처리
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.group_conversations import (
    ALLOWED_ATTACHMENT_MIME,
    ATTACHMENT_MAX_BYTES,
    AttachmentPresignRequest,
    _generate_presign,
)
from app.core.errors import ApiError


# ── 테스트 1: 허용 MIME 목록 ──────────────────────────────────────────────────


def test_allowed_mime_set():
    """허용 MIME 5종이 모두 포함되어야 한다."""
    expected = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
    }
    assert expected == ALLOWED_ATTACHMENT_MIME


# ── 테스트 2: 금지 MIME → 422 ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_invalid_mime_raises_422():
    """지원하지 않는 MIME 타입 → 422 ApiError."""
    forbidden_mimes = ["video/mp4", "audio/mpeg", "text/html", "application/zip"]

    for mime in forbidden_mimes:
        body = AttachmentPresignRequest(
            filename="file.mp4",
            content_type=mime,
            size_bytes=1024,
        )
        with pytest.raises(ApiError) as exc:
            await _generate_presign(uuid.uuid4(), body, "dm-attachments")
        assert exc.value.status_code == 422, f"Expected 422 for MIME: {mime}"


# ── 테스트 3: 10MB 이하 파일 → 허용 ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_within_size_limit_succeeds():
    """10MB 이하 파일 → presign 발급 성공."""
    mock_presigned = MagicMock()
    mock_presigned.url = "https://s3.example.com/presigned"
    mock_presigned.key = "dm-attachments/test.jpg"

    body = AttachmentPresignRequest(
        filename="photo.jpg",
        content_type="image/jpeg",
        size_bytes=5 * 1024 * 1024,  # 5MB
    )

    with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
        mock_provider = MagicMock()
        mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
        mock_storage.return_value = mock_provider

        result = await _generate_presign(uuid.uuid4(), body, "dm-attachments")

    assert "upload_url" in result["data"]
    assert result["data"]["expires_in"] == 900


# ── 테스트 4: 10MB 초과 → 422 ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_exceeds_size_limit_raises_422():
    """10MB 초과 → 422 ApiError."""
    body = AttachmentPresignRequest(
        filename="large.pdf",
        content_type="application/pdf",
        size_bytes=ATTACHMENT_MAX_BYTES + 1,  # 1바이트 초과
    )

    with pytest.raises(ApiError) as exc:
        await _generate_presign(uuid.uuid4(), body, "dm-attachments")

    assert exc.value.status_code == 422
    assert "10MB" in str(exc.value.error_message) or "10" in str(exc.value.error_message)


# ── 테스트 5: presign 응답 구조 ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_response_structure():
    """presign 응답에 upload_url, key, expires_in 포함."""
    conv_id = uuid.uuid4()
    mock_presigned = MagicMock()
    mock_presigned.url = "https://bucket.s3.amazonaws.com/upload"
    mock_presigned.key = f"dm-attachments/{conv_id}/abc.png"

    body = AttachmentPresignRequest(
        filename="image.png",
        content_type="image/png",
        size_bytes=2 * 1024 * 1024,  # 2MB
    )

    with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
        mock_provider = MagicMock()
        mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
        mock_storage.return_value = mock_provider

        result = await _generate_presign(conv_id, body, "dm-attachments")

    data = result["data"]
    assert "upload_url" in data
    assert "key" in data
    assert "expires_in" in data
    assert data["expires_in"] == 900  # 15분


# ── 테스트 6: 경계값 — 정확히 10MB ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_exactly_10mb_allowed():
    """정확히 10MB → 허용 (경계값 포함)."""
    mock_presigned = MagicMock()
    mock_presigned.url = "https://s3.example.com/presigned"
    mock_presigned.key = "dm-attachments/exact10mb.jpg"

    body = AttachmentPresignRequest(
        filename="exact10mb.jpg",
        content_type="image/jpeg",
        size_bytes=ATTACHMENT_MAX_BYTES,  # 정확히 10MB
    )

    with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
        mock_provider = MagicMock()
        mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
        mock_storage.return_value = mock_provider

        # 예외 없이 정상 처리되어야 함
        result = await _generate_presign(uuid.uuid4(), body, "dm-attachments")

    assert result["data"]["expires_in"] == 900


# ── 테스트 7: 파일명 특수문자 ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_special_chars_in_filename():
    """파일명에 특수문자/한글 포함 → 정상 처리."""
    mock_presigned = MagicMock()
    mock_presigned.url = "https://s3.example.com/presigned"
    mock_presigned.key = "dm-attachments/내사진.jpg"

    body = AttachmentPresignRequest(
        filename="내 사진 (2026).jpg",
        content_type="image/jpeg",
        size_bytes=1024,
    )

    with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
        mock_provider = MagicMock()
        mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
        mock_storage.return_value = mock_provider

        result = await _generate_presign(uuid.uuid4(), body, "dm-attachments")

    assert "upload_url" in result["data"]


# ── 테스트 8: ATTACHMENT_MAX_BYTES 상수 값 확인 ───────────────────────────────


def test_attachment_max_bytes_constant():
    """ATTACHMENT_MAX_BYTES가 10MB (10485760 bytes)여야 한다."""
    assert ATTACHMENT_MAX_BYTES == 10 * 1024 * 1024
    assert ATTACHMENT_MAX_BYTES == 10_485_760


# ── 테스트 9: webp, gif 허용 확인 ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_presign_webp_and_gif_allowed():
    """webp, gif MIME → 허용."""
    for mime in ["image/webp", "image/gif"]:
        mock_presigned = MagicMock()
        mock_presigned.url = "https://s3.example.com/presigned"
        mock_presigned.key = f"dm-attachments/test.{mime.split('/')[1]}"

        body = AttachmentPresignRequest(
            filename=f"test.{mime.split('/')[1]}",
            content_type=mime,
            size_bytes=512 * 1024,
        )

        with patch("app.api.group_conversations.get_storage_provider") as mock_storage:
            mock_provider = MagicMock()
            mock_provider.presign_post = AsyncMock(return_value=mock_presigned)
            mock_storage.return_value = mock_provider

            result = await _generate_presign(uuid.uuid4(), body, "dm-attachments")

        assert result["data"]["expires_in"] == 900, f"Expected success for MIME: {mime}"
