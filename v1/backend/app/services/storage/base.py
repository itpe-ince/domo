"""Storage provider interface (Phase 4 M4).

Reference: phase4.design.md §5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StoredObject:
    """Result of a storage write."""

    provider: str          # 'local' | 's3'
    key: str               # storage-internal path/key (e.g. "uploads/2026/04/user/abc.jpg")
    url: str               # publicly accessible URL
    size_bytes: int
    content_type: str


@dataclass
class PresignedPost:
    """Credentials for a direct browser-to-storage upload (POST).

    The client POSTs a multipart/form-data with ``fields`` plus the file
    to ``url``. On success the browser has uploaded directly to storage
    and the backend only needs to be notified via POST /media/finalize.
    """

    url: str               # POST target URL
    fields: dict           # form fields to include (policy, signature, etc.)
    key: str               # storage key the file will land at


class StorageProvider(ABC):
    """Abstract storage provider — local, S3, etc."""

    name: str

    @abstractmethod
    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        """Write bytes to storage at the given key."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete object at key."""

    @abstractmethod
    def public_url(self, key: str) -> str:
        """Return a publicly accessible URL for the given key."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if the object exists."""

    @abstractmethod
    async def presign_post(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int = 200 * 1024 * 1024,
        expires_in: int = 3600,
    ) -> PresignedPost:
        """Return presigned POST credentials for direct client upload."""
