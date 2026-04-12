"""Public guardian consent endpoints (Phase 4 M5).

These are token-based and do NOT require authentication —
the guardian clicks a magic link from their email.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.db.session import get_db
from app.models.guardian import GuardianConsent
from app.services.guardian import approve_consent, withdraw_consent

router = APIRouter(prefix="/guardian", tags=["guardian"])


@router.get("/consent/{token}")
async def get_consent_info(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public — guardian opens magic link, we show minor's details."""
    result = await db.execute(
        select(GuardianConsent).where(GuardianConsent.consent_token == token)
    )
    consent = result.scalar_one_or_none()
    if not consent:
        raise ApiError("NOT_FOUND", "Invalid or expired link", http_status=404)

    # Lazy import to avoid circular imports
    from app.models.user import User

    user_result = await db.execute(
        select(User).where(User.id == consent.minor_user_id)
    )
    minor = user_result.scalar_one_or_none()
    minor_info = None
    if minor:
        minor_info = {
            "display_name": minor.display_name,
            "email": minor.email,
            "birth_year": minor.birth_year,
            "country_code": minor.country_code,
        }

    return {
        "data": {
            "id": str(consent.id),
            "minor": minor_info,
            "guardian_email": consent.guardian_email,
            "guardian_name": consent.guardian_name,
            "consented_at": consent.consented_at.isoformat()
            if consent.consented_at
            else None,
            "withdrawn_at": consent.withdrawn_at.isoformat()
            if consent.withdrawn_at
            else None,
            "expires_at": consent.expires_at.isoformat(),
        }
    }


@router.post("/consent/{token}/approve")
async def approve(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        consent = await approve_consent(db, token)
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", str(e), http_status=422) from e

    await db.commit()
    return {
        "data": {
            "id": str(consent.id),
            "consented_at": consent.consented_at.isoformat()
            if consent.consented_at
            else None,
            "status": "approved",
        }
    }


@router.post("/consent/{token}/withdraw")
async def withdraw(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        consent = await withdraw_consent(db, token)
    except ValueError as e:
        raise ApiError("VALIDATION_ERROR", str(e), http_status=422) from e

    await db.commit()
    return {
        "data": {
            "id": str(consent.id),
            "withdrawn_at": consent.withdrawn_at.isoformat()
            if consent.withdrawn_at
            else None,
            "status": "withdrawn",
        }
    }
