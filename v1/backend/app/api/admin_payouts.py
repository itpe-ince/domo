"""Admin Payouts API — Phase 12 B-3.

6 endpoints:
  GET  /admin/kyc/pending                        — KYC 검수 대기 큐 (FIFO)
  POST /admin/kyc/{user_id}/approve              — KYC 승인 + Stripe Connect onboarding 트리거
  POST /admin/kyc/{user_id}/reject               — KYC 거부 + 사유
  GET  /admin/settlements                        — 월별 정산 이력 (필터: month, artist_id, status)
  GET  /admin/settlements/{id}                   — 정산 상세 (Stripe transfer 정보)
  GET  /admin/stripe-connect/{artist_id}/status  — Stripe Connect 계정 상태

모든 endpoint: require_admin_with_2fa + audit_log
Stripe API 미설정/실패 시 mock 데이터 graceful 반환.
"""
from __future__ import annotations

import logging
import uuid
from calendar import monthrange
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_deps import require_admin_with_2fa
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.kyc import KYCSession
from app.models.notification import Notification
from app.models.settlement import Settlement, SettlementItem
from app.models.user import User
from app.services.audit_log import record_audit

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-payouts"])


# ─────────────────────────────────────────────────────────────────────────────
# Stripe graceful helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_stripe_connect_status() -> dict:
    return {
        "charges_enabled": False,
        "payouts_enabled": False,
        "requirements": {
            "currently_due": ["stripe_not_configured"],
            "eventually_due": [],
            "disabled_reason": None,
        },
        "mock_mode": True,
    }


async def _fetch_stripe_connect_status(stripe_account_id: str | None) -> dict:
    """Stripe Connect 계정 상태 조회. 미설정/실패 시 mock 반환."""
    settings = get_settings()
    if not stripe_account_id or settings.payment_provider != "stripe":
        return _mock_stripe_connect_status()

    try:
        from app.services.payments.stripe_real import StripeProvider
        provider = StripeProvider()
        status = await provider.get_connect_account_status(stripe_account_id)
        status["mock_mode"] = False
        return status
    except Exception as exc:
        log.warning("Stripe Connect status fetch failed for %s: %s", stripe_account_id, exc)
        return _mock_stripe_connect_status()


async def _create_stripe_connect_onboarding(
    *,
    user_id: str, email: str
) -> tuple[str | None, str | None]:
    """Stripe Connect Express 계정 생성 + onboarding URL.
    Returns (account_id, onboarding_url). 미설정/실패 시 (None, None)."""
    settings = get_settings()
    if settings.payment_provider != "stripe":
        return None, None

    try:
        from app.services.payments.stripe_real import StripeProvider
        provider = StripeProvider()
        account_id = await provider.get_or_create_connect_account(user_id, email)
        frontend_url = getattr(settings, "frontend_url", "http://localhost:3700")
        onboarding_url = await provider.create_account_link(
            account_id,
            refresh_url=f"{frontend_url}/settings/stripe-connect?refresh=1",
            return_url=f"{frontend_url}/settings/stripe-connect?success=1",
        )
        return account_id, onboarding_url
    except Exception as exc:
        log.warning("Stripe Connect onboarding failed for user %s: %s", user_id, exc)
        return None, None


async def _fetch_stripe_transfer(payout_reference: str | None) -> dict | None:
    """Stripe Transfer 조회. mock_payout 또는 미설정 시 None."""
    if not payout_reference:
        return None
    if payout_reference.startswith("MOCK_PAYOUT_"):
        return None

    settings = get_settings()
    if settings.payment_provider != "stripe":
        return None

    try:
        from app.services.payments.stripe_real import StripeProvider
        provider = StripeProvider()
        return await provider.retrieve_transfer(payout_reference)
    except Exception as exc:
        log.warning("Stripe Transfer retrieve failed for %s: %s", payout_reference, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/kyc/pending
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/kyc/pending")
async def get_kyc_pending(
    *,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """KYC 검수 대기 큐 (FIFO — 신청 순, pending 세션 + 미인증 사용자)."""

    # 총 건수
    count_stmt = (
        select(func.count(KYCSession.id))
        .join(User, User.id == KYCSession.user_id)
        .where(
            KYCSession.status == "pending",
            User.identity_verified_at.is_(None),
        )
    )
    total: int = (await db.execute(count_stmt)).scalar_one()

    # 데이터 조회
    stmt = (
        select(
            KYCSession.id.label("kyc_session_id"),
            KYCSession.user_id,
            KYCSession.provider,
            KYCSession.created_at,
            User.email.label("user_email"),
            User.display_name.label("user_display_name"),
            User.identity_verified_at,
            User.stripe_customer_id,
        )
        .join(User, User.id == KYCSession.user_id)
        .where(
            KYCSession.status == "pending",
            User.identity_verified_at.is_(None),
        )
        .order_by(KYCSession.created_at.asc())  # FIFO
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).mappings().all()

    await record_audit(
        db,
        actor=admin,
        action="admin.kyc.queue_viewed",
        metadata={"offset": offset, "limit": limit, "total": total},
        request=request,
    )

    return {
        "data": [
            {
                "kyc_session_id": str(r["kyc_session_id"]),
                "user_id": str(r["user_id"]),
                "user_email": r["user_email"],
                "user_display_name": r["user_display_name"],
                "provider": r["provider"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "identity_verified_at": (
                    r["identity_verified_at"].isoformat()
                    if r["identity_verified_at"]
                    else None
                ),
                "stripe_customer_id": r["stripe_customer_id"],
            }
            for r in rows
        ],
        "pagination": {"total": total, "offset": offset, "limit": limit},
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /admin/kyc/{user_id}/approve
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/kyc/{user_id}/approve")
async def approve_kyc(
    *,
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """KYC 승인 → Stripe Connect onboarding 트리거 + audit_log."""

    # 1. 대상 사용자 조회
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise ApiError("USER_NOT_FOUND", "User not found", http_status=404)

    # 2. 이미 인증된 경우
    if user.identity_verified_at is not None:
        raise ApiError("ALREADY_APPROVED", "KYC already approved for this user", http_status=409)

    # 3. 최신 pending 세션 조회
    session_result = await db.execute(
        select(KYCSession)
        .where(KYCSession.user_id == user_id, KYCSession.status == "pending")
        .order_by(KYCSession.created_at.desc())
        .limit(1)
    )
    kyc_session = session_result.scalar_one_or_none()
    if not kyc_session:
        raise ApiError("KYC_SESSION_NOT_FOUND", "No pending KYC session found", http_status=404)

    now = datetime.now(timezone.utc)

    # 4. 세션 상태 업데이트
    kyc_session.status = "verified"
    kyc_session.completed_at = now

    # 5. 사용자 인증 상태 업데이트
    user.identity_verified_at = now
    user.identity_provider = kyc_session.provider

    await db.flush()

    # 6. Stripe Connect onboarding (graceful)
    account_id, onboarding_url = await _create_stripe_connect_onboarding(
        str(user_id), user.email
    )

    # 7. 알림 생성
    notification = Notification(
        user_id=user_id,
        type="kyc_approved",
        title="KYC 인증이 승인되었습니다",
        body="본인 인증이 완료되어 정산 서비스를 이용할 수 있습니다.",
        link="/settings/identity",
    )
    db.add(notification)

    await db.commit()

    await record_audit(
        db,
        actor=admin,
        action="admin.kyc.approved",
        target_type="user",
        target_id=user_id,
        metadata={"provider": kyc_session.provider, "stripe_account_id": account_id},
        request=request,
    )

    return {
        "data": {
            "user_id": str(user_id),
            "kyc_approved_at": now.isoformat(),
            "stripe_connect_onboarding_url": onboarding_url,
            "provider": kyc_session.provider,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /admin/kyc/{user_id}/reject
# ─────────────────────────────────────────────────────────────────────────────

class KYCRejectBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


@router.post("/kyc/{user_id}/reject")
async def reject_kyc(
    *,
    user_id: uuid.UUID,
    body: KYCRejectBody,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """KYC 거부 + 사유 저장 + 재신청 안내 알림 + audit_log."""

    # 1. 대상 사용자 조회
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise ApiError("USER_NOT_FOUND", "User not found", http_status=404)

    # 2. 최신 pending 세션 조회
    session_result = await db.execute(
        select(KYCSession)
        .where(KYCSession.user_id == user_id, KYCSession.status == "pending")
        .order_by(KYCSession.created_at.desc())
        .limit(1)
    )
    kyc_session = session_result.scalar_one_or_none()
    if not kyc_session:
        raise ApiError("NO_PENDING_KYC", "No pending KYC session found", http_status=409)

    now = datetime.now(timezone.utc)

    # 3. 세션 상태 업데이트
    kyc_session.status = "failed"
    kyc_session.completed_at = now
    kyc_session.result_data = {
        "admin_reject_reason": body.reason,
        "rejected_by": str(admin.id),
    }

    # 4. 알림 생성
    notification = Notification(
        user_id=user_id,
        type="kyc_rejected",
        title="KYC 인증이 거부되었습니다",
        body=f"사유: {body.reason}. 수정 후 재신청해 주세요.",
        link="/settings/identity",
    )
    db.add(notification)

    await db.commit()

    await record_audit(
        db,
        actor=admin,
        action="admin.kyc.rejected",
        target_type="user",
        target_id=user_id,
        metadata={"reason": body.reason},
        request=request,
    )

    return {
        "data": {
            "user_id": str(user_id),
            "kyc_rejected_at": now.isoformat(),
            "reason": body.reason,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/settlements
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/settlements")
async def list_settlements(
    *,
    month: str | None = Query(None, description="YYYY-MM 형식"),
    artist_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="pending|approved|paid|failed"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """월별 정산 이력 조회 (필터: month, artist_id, status)."""

    from datetime import date

    conditions = []

    # month 파라미터 → period_start 범위 필터
    if month:
        try:
            year, mon = int(month[:4]), int(month[5:7])
            period_start = date(year, mon, 1)
            _, last_day = monthrange(year, mon)
            period_end = date(year, mon, last_day)
            conditions.extend([
                Settlement.period_start >= period_start,
                Settlement.period_end <= period_end,
            ])
        except (ValueError, IndexError):
            raise ApiError("INVALID_MONTH", "month 형식은 YYYY-MM이어야 합니다", http_status=422)

    if artist_id:
        conditions.append(Settlement.artist_id == artist_id)

    if status:
        conditions.append(Settlement.status == status)

    where_clause = and_(*conditions) if conditions else True

    # 총 건수
    count_stmt = (
        select(func.count(Settlement.id))
        .join(User, User.id == Settlement.artist_id)
        .where(where_clause)
    )
    total: int = (await db.execute(count_stmt)).scalar_one()

    # 데이터 조회
    stmt = (
        select(
            Settlement,
            User.display_name.label("artist_name"),
            User.email.label("artist_email"),
        )
        .join(User, User.id == Settlement.artist_id)
        .where(where_clause)
        .order_by(Settlement.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    # filter 파라미터 구성 (audit_log metadata)
    filter_meta: dict = {"offset": offset, "limit": limit}
    if month:
        filter_meta["month"] = month
    if artist_id:
        filter_meta["artist_id"] = str(artist_id)
    if status:
        filter_meta["status"] = status

    await record_audit(
        db,
        actor=admin,
        action="admin.settlement.list_viewed",
        metadata=filter_meta,
        request=request,
    )

    export_qs = f"?format=csv"
    if month:
        export_qs += f"&month={month}"

    return {
        "data": [
            {
                "id": str(s.id),
                "artist_id": str(s.artist_id),
                "artist_name": artist_name,
                "artist_email": artist_email,
                "period_start": s.period_start.isoformat() if s.period_start else None,
                "period_end": s.period_end.isoformat() if s.period_end else None,
                "order_count": s.order_count,
                "gross_amount": str(s.gross_amount),
                "platform_fee": str(s.platform_fee),
                "net_amount": str(s.net_amount),
                "currency": s.currency,
                "status": s.status,
                "approved_at": s.approved_at.isoformat() if s.approved_at else None,
                "paid_at": s.paid_at.isoformat() if s.paid_at else None,
                "payout_reference": s.payout_reference,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s, artist_name, artist_email in rows
        ],
        "pagination": {"total": total, "offset": offset, "limit": limit},
        "export_url": f"/admin/settlements/export{export_qs}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/settlements/{id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/settlements/{settlement_id}")
async def get_settlement_detail(
    *,
    settlement_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """정산 상세 조회 (settlement_items + Stripe transfer 정보)."""

    # Settlement + artist 조회
    stmt = (
        select(Settlement, User.display_name.label("artist_name"))
        .join(User, User.id == Settlement.artist_id)
        .where(Settlement.id == settlement_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise ApiError("SETTLEMENT_NOT_FOUND", "Settlement not found", http_status=404)

    settlement, artist_name = row

    # settlement_items 조회
    items_stmt = select(SettlementItem).where(SettlementItem.settlement_id == settlement_id)
    items_rows = (await db.execute(items_stmt)).scalars().all()

    # Stripe Transfer 조회 (graceful)
    stripe_transfer = await _fetch_stripe_transfer(settlement.payout_reference)

    await record_audit(
        db,
        actor=admin,
        action="admin.settlement.detail_viewed",
        target_type="settlement",
        target_id=settlement_id,
        request=request,
    )

    return {
        "data": {
            "id": str(settlement.id),
            "artist_id": str(settlement.artist_id),
            "artist_name": artist_name,
            "period_start": settlement.period_start.isoformat() if settlement.period_start else None,
            "period_end": settlement.period_end.isoformat() if settlement.period_end else None,
            "order_count": settlement.order_count,
            "gross_amount": str(settlement.gross_amount),
            "platform_fee": str(settlement.platform_fee),
            "net_amount": str(settlement.net_amount),
            "currency": settlement.currency,
            "status": settlement.status,
            "approved_at": settlement.approved_at.isoformat() if settlement.approved_at else None,
            "paid_at": settlement.paid_at.isoformat() if settlement.paid_at else None,
            "payout_reference": settlement.payout_reference,
            "items": [
                {
                    "order_id": str(item.order_id),
                }
                for item in items_rows
            ],
            "stripe_transfer": stripe_transfer,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /admin/stripe-connect/{artist_id}/status
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stripe-connect/{artist_id}/status")
async def get_stripe_connect_status(
    *,
    artist_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_admin_with_2fa),
    db: AsyncSession = Depends(get_db),
):
    """Stripe Connect 계정 상태 fetch (현재 시점). 미설정 시 mock 반환."""

    # 사용자 조회
    user_result = await db.execute(select(User).where(User.id == artist_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise ApiError("USER_NOT_FOUND", "User not found", http_status=404)

    # Stripe Connect 계정 상태 조회 (graceful)
    stripe_status = await _fetch_stripe_connect_status(user.stripe_customer_id)

    await record_audit(
        db,
        actor=admin,
        action="admin.stripe_connect.status_checked",
        target_type="user",
        target_id=artist_id,
        metadata={"mock_mode": stripe_status.get("mock_mode", True)},
        request=request,
    )

    return {
        "data": {
            "artist_id": str(artist_id),
            "artist_name": user.display_name,
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_connect_account_id": None,  # Phase 13에서 별도 컬럼 추가 예정
            **stripe_status,
        }
    }
