from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://domo:domo_dev_pw@localhost:5432/domo"
    # Redis / Cache (G''-2 redis-cache-layer)
    # Set REDIS_URL to enable Redis; leave unset for in-memory fallback (dev/CI).
    redis_url: str | None = None
    redis_password: str | None = None
    redis_max_connections: int = 50

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

    # Observability / Prometheus
    # Set METRICS_ENABLED=true and METRICS_TOKEN=<secret> to expose /metrics.
    # Without METRICS_ENABLED=true the endpoint returns 503.
    # When enabled, Authorization: Bearer <METRICS_TOKEN> is required.
    metrics_enabled: bool = False
    metrics_token: str = ""

    # Analytics — PostHog (G'-4 backend-posthog-integration)
    # Server-side key (different from NEXT_PUBLIC_POSTHOG_KEY used by frontend).
    # Leave empty to enable Mock mode (console log only, no SDK calls).
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"

    # LLM Gateway — C-1 ai-artist-interview-generation (tuzigroup)
    # Leave llm_gateway_api_key empty to enable Mock mode (returns placeholder interview).
    # backend .env: set LLM_GATEWAY_URL, LLM_GATEWAY_API_KEY, LLM_MODEL_NAME
    llm_gateway_url: str = "https://llm.tuzigroup.com/v1"
    llm_gateway_api_key: str = ""  # gw-qrCBDLsiz0IN5_QVksHuptT8Vg6kDKrPdQwQz6L-ZaU
    llm_model_name: str = "gemma4-e4b"

    # AWS SES — C-5 newsletter-digest
    # Leave aws_ses_access_key_id empty to enable Mock mode (logs email, no AWS calls).
    # NOTE: aws_access_key_id / aws_secret_access_key (without ses_ prefix) are used
    # for S3 storage.  SES uses dedicated credentials for least-privilege separation.
    aws_ses_region: str = "us-east-1"
    aws_ses_access_key_id: str = ""
    aws_ses_secret_access_key: str = ""
    aws_ses_from_address: str = "noreply@domo.art"

    # Open Exchange Rates API — B'-1 multi-currency-foundation
    # Get free APP_ID at https://openexchangerates.org (1000 req/month free).
    # If unset, exchange_rate_cron_loop uses Mock mode (hardcoded rates).
    exchange_rate_api_key: str = ""

    # AWS SNS — H'-5 newsletter-bounce-handling
    # SNS delivers SES bounce/complaint/delivery events to POST /v1/webhooks/ses-bounce.
    # Leave aws_sns_topic_arn empty to skip signature verification in dev/test.
    # Production: set to the ARN of the SNS topic configured in SES event destinations.
    aws_sns_topic_arn: str = ""

    # Admin alert email for complaint events (H'-5)
    # When a complaint is received, an alert is sent to this address.
    admin_alert_email: str = ""

    # OpenTelemetry — G''-1 opentelemetry-tracing
    # Set OTEL_ENABLED=true to activate distributed tracing.
    # Production (AWS X-Ray): OTEL_OTLP_ENDPOINT=localhost:4317 (ADOT sidecar).
    # Mock mode (default): all OTel calls are no-op, zero performance overhead.
    otel_enabled: bool = False
    otel_service_name: str = "domo-backend"
    otel_otlp_endpoint: str | None = None  # e.g. localhost:4317 (ADOT Collector)
    otel_sampling_rate: float = 0.1  # 10% production; set 1.0 for staging/dev

    # Firebase / FCM — B'-3 push-email-digest-foundation
    # Leave firebase_credentials_json empty to enable Mock mode (logs push, no FCM calls).
    # Production: set to the JSON contents of your Firebase service account key.
    firebase_credentials_json: str = ""

    # APNs (Apple Push Notification service) — B'-3 push-email-digest-foundation
    # Leave apns_key_id empty to enable Mock mode.
    apns_key_id: str = ""          # 10-char key ID from Apple Developer portal
    apns_team_id: str = ""         # 10-char team ID
    apns_auth_key_p8: str = ""     # Contents of AuthKey_XXXXXXXX.p8 (ES256 private key)
    apns_bundle_id: str = "art.domo.app"
    apns_sandbox: bool = True      # True = sandbox (dev), False = production

    # AI Artwork Caption — Phase 9 K-3
    # ARTWORK_CAPTION_WORKER_ENABLED=true 시 21번째 cron worker 활성화
    artwork_caption_worker_enabled: bool = True
    # quick sweep 배치 크기 (기본 20, 60초 주기)
    caption_batch_size_quick: int = 20
    # batch sweep 배치 크기 (기본 100, 24h 주기)
    caption_batch_size_batch: int = 100
    # 포스트당 하루 재생성 횟수 제한 (기본 3)
    artwork_caption_daily_limit_per_post: int = 3

    # Cohort Alert — Phase 9 L-F cohort-retention-alert
    # Slack Incoming Webhook URL. 미설정 시 Mock 모드 (log 출력만, 에러 없음).
    slack_webhook_url: str = ""
    # D7 retention 경고 임계값 (기본 30% — roadmap KPI 기준)
    cohort_alert_7d_threshold: float = 0.30
    # D30 retention 경고 임계값 (기본 15% — roadmap KPI 기준)
    cohort_alert_30d_threshold: float = 0.15
    # cohort 최소 크기 — 미만 시 측정 skip (통계 신뢰도 부족)
    cohort_alert_min_cohort_size: int = 10

    # DB Connection Pool — G''-4 db-connection-pool-tuning
    # Default values tuned for production load (≥50 concurrent connections).
    # Override per environment:
    #   dev:        DB_POOL_SIZE=5  DB_MAX_OVERFLOW=10
    #   staging:    DB_POOL_SIZE=10 DB_MAX_OVERFLOW=20
    #   production: DB_POOL_SIZE=20 DB_MAX_OVERFLOW=30  (default)
    db_pool_size: int = 20
    db_max_overflow: int = 30
    db_pool_recycle: int = 3600  # seconds — reconnect stale connections after 1h
    db_pool_timeout: int = 30   # seconds — raise TimeoutError if no connection available


@lru_cache
def get_settings() -> Settings:
    return Settings()
