"""factory_boy 팩토리 — Phase 12 A-1.

MagicMock 대신 실제 SQLAlchemy 모델 인스턴스를 생성하여
Pydantic 직렬화(UserPublic 등) 검증을 통과할 수 있도록 한다.

사용법:
    from tests.factories import UserFactory
    user = UserFactory()                      # 기본값으로 인스턴스 생성
    user = UserFactory(email="a@b.com")       # 필드 오버라이드
    user = UserFactory.build(role="admin")    # DB INSERT 없이 객체만 생성
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import factory

from app.core.security import hash_password
from app.models.user import User


class UserFactory(factory.Factory):
    """User 모델 인스턴스 팩토리.

    factory.Factory (DB 비의존) — 실제 User 객체를 반환.
    UserPublic Pydantic 직렬화에 필요한 모든 필드를 기본값으로 포함.
    """

    class Meta:
        model = User

    # 필수 / 고유 식별자
    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Faker("email")

    # 프로필
    display_name = factory.Sequence(lambda n: f"user_{n}")
    avatar_url = None
    bio = None
    country_code = "KR"
    language = "ko"

    # 역할 / 상태
    role = "user"
    status = "active"

    # 인증
    sns_provider = None
    sns_id = None
    password_hash = factory.LazyFunction(lambda: hash_password("Secure!Pass9"))
    password_changed_at = None

    # 이메일 인증
    email_verified = True
    email_verification_token = None
    email_verification_sent_at = None
    email_verification_expires_at = None

    # 로그인 실패
    failed_login_count = 0
    failed_login_locked_until = None

    # TOTP / 관리자 2FA
    totp_secret = None
    totp_enabled_at = None
    locked_until = None

    # 개인정보
    birth_year = None
    is_minor = False
    onboarded_at = None
    guardian_id = None
    preferred_genres = None
    identity_verified_at = None
    identity_provider = None
    warning_count = 0
    gdpr_consent_at = None
    signature_storage_key = None

    # 통화
    preferred_currency = "USD"

    # 아티스트 인덱스 (nullable)
    artist_index_score = None
    artist_index_rank = None
    artist_index_rank_region = None
    artist_index_calculated_at = None
    artist_index_score_region = None
    artist_index_rank_genre = None
    artist_index_score_genre = None
    artist_index_primary_genre = None

    # Stripe
    stripe_customer_id = None

    # sponsor
    sponsor_validity_days = None

    # GDPR
    deleted_at = None
    deletion_scheduled_for = None
    gdpr_export_count = 0
    privacy_policy_version = None
    terms_version = None

    # 타임스탬프 (DB server_default 대신 Python 기본값)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
