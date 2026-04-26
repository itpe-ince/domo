"""S3 storage provider (Phase 4 M4).

Reference: phase4.design.md §5.2

This is a full S3 implementation using aioboto3. It is **code-ready**
but requires valid AWS credentials and a bucket to actually run.
When STORAGE_PROVIDER=s3, this provider is selected by the factory.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.services.storage.base import PresignedPost, StoredObject, StorageProvider


class S3StorageProvider(StorageProvider):
    name = "s3"

    def __init__(self):
        settings = get_settings()
        self.bucket = getattr(settings, "s3_bucket", None)
        self.region = getattr(settings, "s3_region", "ap-northeast-2")
        self.cdn_base = getattr(settings, "cdn_base_url", None)
        self.access_key = getattr(settings, "aws_access_key_id", None)
        self.secret_key = getattr(settings, "aws_secret_access_key", None)

        if not self.bucket or not self.access_key:
            raise RuntimeError(
                "S3StorageProvider requires S3_BUCKET and AWS credentials. "
                "Set STORAGE_PROVIDER=local for development."
            )

    def _client(self):
        # Lazy import so that test environments without aioboto3 don't crash
        import aioboto3

        session = aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        return session.client("s3")

    async def put(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        return StoredObject(
            provider=self.name,
            key=key,
            url=self.public_url(key),
            size_bytes=len(data),
            content_type=content_type,
        )

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self.bucket, Key=key)

    def public_url(self, key: str) -> str:
        if self.cdn_base:
            return f"{self.cdn_base.rstrip('/')}/{key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"

    async def exists(self, key: str) -> bool:
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def presign_post(
        self,
        key: str,
        content_type: str,
        max_size_bytes: int = 200 * 1024 * 1024,
        expires_in: int = 3600,
    ) -> PresignedPost:
        """Generate S3 presigned POST credentials for direct client upload."""
        import aioboto3

        session = aioboto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        # aioboto3 generate_presigned_post is sync-wrapped — call via thread
        import asyncio
        import boto3

        def _generate():
            client = boto3.client(
                "s3",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            return client.generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, max_size_bytes],
                ],
                ExpiresIn=expires_in,
            )

        result = await asyncio.to_thread(_generate)
        return PresignedPost(
            url=result["url"],
            fields=result["fields"],
            key=key,
        )
