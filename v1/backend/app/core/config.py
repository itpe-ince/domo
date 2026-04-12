from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://domo:domo_dev_pw@localhost:5432/domo"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    google_client_id: str = ""
    google_client_secret: str = ""

    payment_provider: str = "mock_stripe"  # 'mock_stripe' | 'stripe'
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Storage (Phase 4 M4)
    storage_provider: str = "local"  # 'local' | 's3'
    upload_dir: str = "/app/uploads"  # local storage root (override for host-side dev)
    s3_bucket: str = ""
    s3_region: str = "ap-northeast-2"
    cdn_base_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Email (Phase 4 M5)
    email_provider: str = "mock"  # 'mock' | 'resend' | 'ses'
    resend_api_key: str = ""
    email_from: str = "noreply@domo.tuzigroup.com"

    frontend_url: str = "http://localhost:3700"


@lru_cache
def get_settings() -> Settings:
    return Settings()
