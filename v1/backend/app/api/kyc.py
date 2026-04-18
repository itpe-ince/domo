"""KYC (Identity Verification) API."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.kyc import KYCSession
from app.models.user import User
from app.services.kyc import MockKYCProvider, get_kyc_provider

router = APIRouter(prefix="/kyc", tags=["kyc"])


@router.get("/status")
async def kyc_status(
    user: User = Depends(get_current_user),
):
    return {
        "data": {
            "verified": user.identity_verified_at is not None,
            "provider": user.identity_provider,
            "verified_at": user.identity_verified_at.isoformat() if user.identity_verified_at else None,
        }
    }


class KYCStartRequest(BaseModel):
    redirect_url: str = ""


@router.post("/start")
async def start_kyc(
    body: KYCStartRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.identity_verified_at:
        return {"data": {"already_verified": True, "provider": user.identity_provider}}

    provider = get_kyc_provider()
    result = await provider.start_verification(str(user.id), body.redirect_url)

    session = KYCSession(
        user_id=user.id,
        provider=result.provider,
        external_session_id=result.session_id,
        status="pending",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "data": {
            "session_id": str(session.id),
            "redirect_url": result.redirect_url,
            "provider": result.provider,
        }
    }


class MockVerifyRequest(BaseModel):
    name: str
    birth_date: str  # YYYY-MM-DD


@router.post("/mock-verify")
async def mock_verify(
    body: MockVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Development only: instant identity verification."""
    provider = get_kyc_provider()
    if not isinstance(provider, MockKYCProvider):
        raise ApiError("FORBIDDEN", "Mock verification only available in development", http_status=403)

    result = await provider.mock_verify(body.name, body.birth_date)
    if not result.verified:
        raise ApiError("VERIFICATION_FAILED", result.error or "Verification failed", http_status=422)

    now = datetime.now(timezone.utc)
    user.identity_verified_at = now
    user.identity_provider = "mock"

    # Record session
    session = KYCSession(
        user_id=user.id,
        provider="mock",
        status="verified",
        result_data={"name": body.name, "birth_date": body.birth_date},
        completed_at=now,
    )
    db.add(session)
    await db.commit()

    return {
        "data": {
            "verified": True,
            "provider": "mock",
            "name": body.name,
        }
    }
