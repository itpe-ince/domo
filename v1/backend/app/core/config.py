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
    email_provider: str = "mock"  # 'mock' | 'resend' | 'smtp'
    resend_api_key: str = ""
    email_from: str = "noreply@domo.tuzigroup.com"
    email_from_address: str = ""   # falls back to smtp_user / email_from
    email_from_name: str = "Domo"

    # SMTP (Gmail / Google Workspace / generic SMTP relay)
    smtp_host: str = ""              # e.g. smtp.gmail.com
    smtp_port: int = 587              # 587 STARTTLS / 465 SSL
    smtp_user: str = ""               # e.g. no-reply@tuzigroup.com
    smtp_password: str = ""           # 16-char Gmail App Password
    smtp_use_tls: bool = True         # STARTTLS on 587 (default)
    smtp_use_ssl: bool = False        # implicit SSL on 465 (mutually exclusive with TLS)

    # KYC — 'mock' | 'toss' | 'stripe'
    kyc_provider: str = "mock"
    toss_client_id: str = ""
    toss_client_secret: str = ""

    # Translation — 'auto' | 'ollama' | 'google' | 'mock'
    translation_provider: str = "auto"
    google_translate_api_key: str = ""
    ollama_url: str = "http://100.75.139.86:11434"
    ollama_translation_model: str = "gemma4:latest"

    frontend_url: str = "http://localhost:3700"
    admin_url: str = "http://localhost:3800"
    # Backend's own externally-reachable API URL (includes /v1).
    # Storage providers append /media/files/{key} etc. to this.
    # Frontend/admin use their own NEXT_PUBLIC_API_URL (Next.js convention) —
    # values should match but are managed in their own .env.local files.
    # Production: set API_URL=https://domo-api.tuzigroup.com/v1
    api_url: str = "http://localhost:3710/v1"

    @property
    def api_base_url(self) -> str:
        """Alias kept for clarity in storage providers. Same as api_url."""
        return self.api_url.rstrip("/")
    # Optional comma-separated extra origins for staging/preview deployments
    extra_cors_origins: str = ""

    # Fernet key (URL-safe base64, 32 bytes) for encrypting admin TOTP secrets
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # If empty, secrets are stored as plaintext (dev only — emits warning at boot).
    totp_encryption_key: str = ""

    # WebAuthn / Passkey Relying Party config.
    # rp_id MUST match the domain the admin browser is loaded from (no scheme/port).
    # For dev: "localhost". For production: e.g. "admin.domo.art".
    # rp_origin includes scheme + port (browser checks this strictly).
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Domo Admin"
    webauthn_rp_origin: str = "http://localhost:3800"


@lru_cache
def get_settings() -> Settings:
    return Settings()
