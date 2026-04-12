"""Storage provider factory.

STORAGE_PROVIDER env var:
- 'local' (default) → LocalStorageProvider (/app/uploads)
- 's3' → S3StorageProvider (requires AWS credentials)
"""
from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider


@lru_cache
def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    provider = getattr(settings, "storage_provider", "local")

    if provider == "s3":
        from app.services.storage.s3 import S3StorageProvider

        return S3StorageProvider()

    return LocalStorageProvider()
