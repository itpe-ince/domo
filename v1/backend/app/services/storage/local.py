"""Local filesystem storage provider (Phase 4 M4).

Wraps the configured upload_dir with the StorageProvider interface.
Keys are relative paths; public URLs go through /v1/media/files/{path}.

Default upload_dir is "/app/uploads" (Docker). Host-side dev sets UPLOAD_DIR
env var to a project-local path like "backend/uploads".
"""
from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.services.storage.base import PresignedPost, StoredObject, StorageProvider

# Resolved at import time from current settings.
UPLOAD_ROOT = Path(get_settings().upload_dir)


class LocalStorageProvider(StorageProvider):
    name = "local"

    def __init__(self, root: Path = UPLOAD_ROOT):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        # Safety: reject keys that try to escape root
        safe_key = key.lstrip("/")
        if ".." in Path(safe_key).parts:
            raise ValueError(f"Invalid key (path traversal): {key}")

        path = self.root / safe_key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

        return StoredObject(
            provider=self.name,
            key=safe_key,
            url=self.public_url(safe_key),
            size_bytes=len(data),
            content_type=content_type,
        )

    async def delete(self, key: str) -> None:
        safe_key = key.lstrip("/")
        path = self.root / safe_key
        if path.exists():
            path.unlink()

    def public_url(self, key: str) -> str:
        safe_key = key.lstrip("/")
        return f"/v1/media/files/{safe_key}"

    async def exists(self, key: str) -> bool:
        safe_key = key.lstrip("/")
        return (self.root / safe_key).exists()

    async def presign_post(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int = 200 * 1024 * 1024,
        expires_in: int = 3600,
    ) -> PresignedPost:
        """Local dev stub — returns a local upload URL instead of an S3 presigned POST.

        The client should POST the file directly to /v1/media/upload-local/{key}
        (handled by the finalize endpoint in dev mode). In production, swap to
        S3StorageProvider which returns real presigned POST credentials.
        """
        safe_key = key.lstrip("/")
        return PresignedPost(
            url=f"/v1/media/upload-local",
            fields={"key": safe_key, "content_type": content_type},
            key=safe_key,
        )
