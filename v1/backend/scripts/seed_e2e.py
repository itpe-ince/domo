"""Seed deterministic accounts for local Playwright E2E tests.

Run from v1/backend:
    ALLOW_E2E_SEED=true python -m scripts.seed_e2e

This script is intentionally guarded so it cannot run by accident.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import encrypt_totp_secret, hash_password
from app.db.session import AsyncSessionLocal
from app.models.user import ArtistApplication, ArtistProfile, User

USER_EMAIL = os.environ.get("E2E_USER_EMAIL", "e2e-user@domo.example.com")
ARTIST_EMAIL = os.environ.get("E2E_ARTIST_EMAIL", "e2e-artist@domo.example.com")
ADMIN_EMAIL = os.environ.get("E2E_ADMIN_EMAIL", "e2e-admin@domo.example.com")
REVIEW_USER_EMAIL = os.environ.get(
    "E2E_REVIEW_USER_EMAIL", "e2e-review@domo.example.com"
)

USER_PASSWORD = os.environ.get("E2E_USER_PASSWORD", "DomoE2EUser!2026")
ARTIST_PASSWORD = os.environ.get("E2E_ARTIST_PASSWORD", "DomoE2EArtist!2026")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "DomoE2EAdmin!2026")
REVIEW_USER_PASSWORD = os.environ.get(
    "E2E_REVIEW_USER_PASSWORD", "DomoE2EReview!2026"
)
ADMIN_TOTP_SECRET = os.environ.get(
    "E2E_ADMIN_TOTP_SECRET", "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
)


def ensure_allowed() -> None:
    if os.environ.get("ALLOW_E2E_SEED") != "true":
        raise SystemExit(
            "Refusing to seed E2E accounts. Set ALLOW_E2E_SEED=true explicitly."
        )


async def upsert_user(
    db,
    *,
    email: str,
    password: str,
    display_name: str,
    role: str,
    country_code: str | None = None,
) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=email,
            display_name=display_name,
            role=role,
            status="active",
            country_code=country_code,
        )
        db.add(user)

    user.password_hash = hash_password(password)
    user.password_changed_at = now
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires_at = None
    user.status = "active"
    user.sns_provider = None
    user.sns_id = None
    await db.flush()
    return user


async def ensure_artist_profile(db, artist: User, admin: User) -> None:
    result = await db.execute(
        select(ArtistProfile).where(ArtistProfile.user_id == artist.id)
    )
    if result.scalar_one_or_none():
        return

    app = ArtistApplication(
        id=uuid.uuid4(),
        user_id=artist.id,
        school="Domo E2E Art School",
        department="Painting",
        graduation_year=2026,
        is_enrolled=True,
        genre_tags=["painting"],
        portfolio_urls=["https://example.com/e2e-portfolio"],
        statement="E2E artist fixture.",
        status="approved",
        reviewed_by=admin.id,
        reviewed_at=datetime.now(timezone.utc),
    )
    db.add(app)
    await db.flush()

    db.add(
        ArtistProfile(
            user_id=artist.id,
            application_id=app.id,
            verified_by=admin.id,
            school=app.school,
            department=app.department,
            graduation_year=app.graduation_year,
            is_enrolled=True,
            genre_tags=app.genre_tags,
            portfolio_urls=app.portfolio_urls,
            statement=app.statement,
            badge_level="emerging",
            payout_country="KR",
        )
    )


async def ensure_pending_review_application(db, user: User) -> None:
    # Reset this deterministic fixture so the cross-app approval test can be
    # re-run after a previous run approved the application.
    user.role = "user"
    result = await db.execute(
        select(ArtistApplication).where(
            ArtistApplication.user_id == user.id,
            ArtistApplication.status == "pending",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return

    db.add(
        ArtistApplication(
            id=uuid.uuid4(),
            user_id=user.id,
            school="Domo E2E Review School",
            department="Painting",
            graduation_year=2026,
            is_enrolled=True,
            genre_tags=["painting"],
            portfolio_urls=["https://example.com/e2e-review-portfolio"],
            statement="E2E pending artist application.",
            status="pending",
        )
    )


async def seed() -> None:
    ensure_allowed()
    async with AsyncSessionLocal() as db:
        admin = await upsert_user(
            db,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            display_name="E2E Admin",
            role="admin",
            country_code="KR",
        )
        admin.totp_secret = encrypt_totp_secret(ADMIN_TOTP_SECRET)
        admin.totp_enabled_at = datetime.now(timezone.utc)

        await upsert_user(
            db,
            email=USER_EMAIL,
            password=USER_PASSWORD,
            display_name="E2E User",
            role="user",
            country_code="KR",
        )
        artist = await upsert_user(
            db,
            email=ARTIST_EMAIL,
            password=ARTIST_PASSWORD,
            display_name="E2E Artist",
            role="artist",
            country_code="KR",
        )
        await ensure_artist_profile(db, artist, admin)
        review_user = await upsert_user(
            db,
            email=REVIEW_USER_EMAIL,
            password=REVIEW_USER_PASSWORD,
            display_name="E2E Review User",
            role="user",
            country_code="KR",
        )
        await ensure_pending_review_application(db, review_user)

        await db.commit()

    print("E2E seed complete.")
    print(f"  user:   {USER_EMAIL}")
    print(f"  artist: {ARTIST_EMAIL}")
    print(f"  review: {REVIEW_USER_EMAIL}")
    print(f"  admin:  {ADMIN_EMAIL}")
    print("  totp:   E2E_ADMIN_TOTP_SECRET")


if __name__ == "__main__":
    asyncio.run(seed())
