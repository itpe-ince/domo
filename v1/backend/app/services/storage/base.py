"""Storage provider interface (Phase 4 M4).

Reference: phase4.design.md §5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredObject:
    """Result of a storage write."""

    provider: str          # 'local' | 's3'
    key: str               # storage-internal path/key (e.g. "uploads/2026/04/user/abc.jpg")
    url: str               # publicly accessible URL
    size_bytes: int
    content_type: str


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
