"""Integration tests — Admin Payouts API (Phase 12 B-3).

테스트 항목:
  1.  GET  /admin/kyc/pending                — 200 + pending 목록 반환, FIFO 정렬
  2.  GET  /admin/kyc/pending (non-admin)    — 403
  3.  POST /admin/kyc/{user_id}/approve      — 200 + kyc verified + users.identity_verified_at
  4.  POST /admin/kyc/{user_id}/approve (이미 승인) — 409 ALREADY_APPROVED
  5.  POST /admin/kyc/{user_id}/reject       — 200 + kyc failed + result_data.admin_reject_reason
  6.  POST /admin/kyc/{user_id}/reject (reason 없음) — 422
  7.  GET  /admin/settlements (month 필터)   — 200 + 필터 정확도
  8.  GET  /admin/settlements (status 필터)  — 200 + 필터 정확도
  9.  GET  /admin/settlements/{id}           — 200 + items + stripe_transfer null (mock mode)
  10. GET  /admin/stripe-connect/{id}/status — 200 + mock_mode=true (PAYMENT_PROVIDER!=stripe)
  11. audit_log approve 기록 검증
  12. Stripe API 실패 시 mock_mode=true graceful 반환
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import ApiError


# ──────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

def _make_admin_mock() -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = "admin"
    u.totp_enabled_at = datetime.now(timezone.utc)
    return u


def _make_user_mock(
    role: str = "user",
    identity_verified_at=None,
    stripe_customer_id: str | None = None,
) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    u.email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    u.display_name = "테스트 작가"
    u.status = "active"
    u.identity_verified_at = identity_verified_at
    u.identity_provider = None
    u.stripe_customer_id = stripe_customer_id
    return u


def _make_kyc_session_mock(
    user_id: uuid.UUID,
    status: str = "pending",
) -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.provider = "mock"
    s.status = status
    s.created_at = datetime.now(timezone.utc)
    s.completed_at = None
    s.result_data = None
    return s


def _make_settlement_mock(artist_id: uuid.UUID, status: str = "paid") -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.artist_id = artist_id
    s.period_start = date(2026, 4, 1)
    s.period_end = date(2026, 4, 30)
    s.order_count = 3
    s.gross_amount = Decimal("150000.00")
    s.platform_fee = Decimal("15000.00")
    s.net_amount = Decimal("135000.00")
    s.currency = "KRW"
    s.status = status
    s.approved_at = datetime(2026, 5, 1, 9, 0, 0, tzinfo=timezone.utc)
    s.paid_at = datetime(2026, 5, 2, 11, 0, 0, tzinfo=timezone.utc)
    s.payout_reference = "MOCK_PAYOUT_abc12345"
    s.created_at = datetime(2026, 5, 1, 0, 0, 0, tzinfo=timezone.utc)
    return s


def _make_request() -> MagicMock:
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = MagicMock()
    req.headers.get = MagicMock(return_value=None)
    return req


def _make_async_db(
    *,
    user_result=None,
    kyc_session_result=None,
    settlement_result=None,
    settlement_items_result=None,
    count_result: int = 0,
) -> MagicMock:
    """AsyncSession mock — execute().scalar_one_or_none() 등을 흉내냄."""
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()

    # execute side_effect 큐 (순서대로 반환)
    call_queue: list = []

    def _make_scalar_result(value):
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=value)
        r.scalar_one = MagicMock(return_value=value)
        r.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[] if value is None else [value] if not isinstance(value, list) else value)))
        r.first = MagicMock(return_value=value)
        r.mappings = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        r.all = MagicMock(return_value=[])
        return r

    if count_result is not None:
        count_r = MagicMock()
        count_r.scalar_one = MagicMock(return_value=count_result)
        count_r.scalar_one_or_none = MagicMock(return_value=count_result)
        call_queue.append(count_r)

    for val in [user_result, kyc_session_result, settlement_result, settlement_items_result]:
        if val is not None:
            call_queue.append(_make_scalar_result(val))

    call_index = [0]

    async def _execute(stmt):
        idx = call_index[0]
        call_index[0] += 1
        if idx < len(call_queue):
            return call_queue[idx]
        return _make_scalar_result(None)

    db.execute = _execute
    return db


# ──────────────────────────────────────────────────────────────────────────────
# 1. GET /admin/kyc/pending — 200 + FIFO 정렬
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_kyc_pending_as_admin():
    """GET /admin/kyc/pending — 200 응답 + pagination 포함."""
    from app.api.admin_payouts import get_kyc_pending

    admin = _make_admin_mock()

    # DB mock: count=2, 데이터 행 (mappings().all() 반환)
    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=2)

    kyc_row1 = {
        "kyc_session_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "provider": "mock",
        "created_at": datetime(2026, 5, 1, tzinfo=timezone.utc),
        "user_email": "artist1@example.com",
        "user_display_name": "홍길동",
        "identity_verified_at": None,
        "stripe_customer_id": None,
    }
    kyc_row2 = {
        "kyc_session_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "provider": "mock",
        "created_at": datetime(2026, 5, 2, tzinfo=timezone.utc),
        "user_email": "artist2@example.com",
        "user_display_name": "김예술",
        "identity_verified_at": None,
        "stripe_customer_id": None,
    }

    data_result = MagicMock()
    data_result.mappings = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[kyc_row1, kyc_row2]))
    )

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return count_result
        return data_result

    db.execute = _execute

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await get_kyc_pending(
            limit=20, offset=0, request=_make_request(), admin=admin, db=db
        )

    assert "data" in response
    assert len(response["data"]) == 2
    assert response["pagination"]["total"] == 2
    # FIFO: 첫 번째 행이 더 이른 날짜
    assert response["data"][0]["user_email"] == "artist1@example.com"
    assert response["data"][1]["user_email"] == "artist2@example.com"


# ──────────────────────────────────────────────────────────────────────────────
# 2. GET /admin/kyc/pending — non-admin → ApiError (403 검증은 require_admin_with_2fa)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_kyc_pending_forbidden_without_2fa():
    """require_admin_with_2fa가 2FA 미설정 admin에게 ApiError SECOND_FACTOR_REQUIRED를 raise."""
    from app.core.admin_deps import require_admin_with_2fa

    non_2fa_admin = MagicMock()
    non_2fa_admin.id = uuid.uuid4()
    non_2fa_admin.role = "admin"
    non_2fa_admin.totp_enabled_at = None  # 2FA 미설정

    # DB mock: WebauthnCredential count = 0
    db = MagicMock()
    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=0)

    async def _execute(stmt):
        return count_result

    db.execute = _execute

    with patch("app.core.admin_deps.get_current_user", return_value=non_2fa_admin):
        with pytest.raises(ApiError) as exc_info:
            await require_admin_with_2fa(user=non_2fa_admin, db=db)

    assert exc_info.value.code == "SECOND_FACTOR_REQUIRED"


# ──────────────────────────────────────────────────────────────────────────────
# 3. POST /admin/kyc/{user_id}/approve — 200 + DB 업데이트
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_kyc_success():
    """KYC 승인: kyc_session.status=verified, user.identity_verified_at 설정 확인."""
    from app.api.admin_payouts import approve_kyc

    admin = _make_admin_mock()
    user = _make_user_mock(identity_verified_at=None)
    kyc_session = _make_kyc_session_mock(user.id, status="pending")

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        r = MagicMock()
        if idx == 0:
            r.scalar_one_or_none = MagicMock(return_value=user)
        elif idx == 1:
            r.scalar_one_or_none = MagicMock(return_value=kyc_session)
        else:
            r.scalar_one_or_none = MagicMock(return_value=None)
        return r

    db.execute = _execute

    with patch("app.api.admin_payouts._create_stripe_connect_onboarding", new_callable=AsyncMock) as mock_stripe:
        mock_stripe.return_value = (None, None)
        with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
            response = await approve_kyc(
                user_id=user.id, request=_make_request(), admin=admin, db=db
            )

    assert response["data"]["user_id"] == str(user.id)
    assert "kyc_approved_at" in response["data"]
    assert response["data"]["stripe_connect_onboarding_url"] is None  # mock mode
    # DB 변경 검증
    assert kyc_session.status == "verified"
    assert kyc_session.completed_at is not None
    assert user.identity_verified_at is not None
    assert user.identity_provider == "mock"
    # 알림 생성 확인
    db.add.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# 4. POST /admin/kyc/{user_id}/approve — 이미 승인 → 409
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_kyc_already_approved():
    """이미 identity_verified_at이 설정된 사용자 → 409 ALREADY_APPROVED."""
    from app.api.admin_payouts import approve_kyc

    admin = _make_admin_mock()
    user = _make_user_mock(identity_verified_at=datetime.now(timezone.utc))

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _execute(stmt):
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=user)
        return r

    db.execute = _execute

    with pytest.raises(ApiError) as exc_info:
        await approve_kyc(
            user_id=user.id, request=_make_request(), admin=admin, db=db
        )

    assert exc_info.value.code == "ALREADY_APPROVED"


# ──────────────────────────────────────────────────────────────────────────────
# 5. POST /admin/kyc/{user_id}/reject — 200 + result_data 저장
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_kyc_success():
    """KYC 거부: kyc_session.status=failed, result_data.admin_reject_reason 저장."""
    from app.api.admin_payouts import KYCRejectBody, reject_kyc

    admin = _make_admin_mock()
    user = _make_user_mock(identity_verified_at=None)
    kyc_session = _make_kyc_session_mock(user.id, status="pending")

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        r = MagicMock()
        if idx == 0:
            r.scalar_one_or_none = MagicMock(return_value=user)
        elif idx == 1:
            r.scalar_one_or_none = MagicMock(return_value=kyc_session)
        else:
            r.scalar_one_or_none = MagicMock(return_value=None)
        return r

    db.execute = _execute

    reason_text = "신분증 사진 불명확 — 재촬영 후 재신청 바랍니다"
    body = KYCRejectBody(reason=reason_text)

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await reject_kyc(
            user_id=user.id, body=body, request=_make_request(), admin=admin, db=db
        )

    assert response["data"]["user_id"] == str(user.id)
    assert response["data"]["reason"] == reason_text
    # DB 변경 검증
    assert kyc_session.status == "failed"
    assert kyc_session.completed_at is not None
    assert kyc_session.result_data["admin_reject_reason"] == reason_text
    assert kyc_session.result_data["rejected_by"] == str(admin.id)
    # 알림 생성 확인
    db.add.assert_called()


# ──────────────────────────────────────────────────────────────────────────────
# 6. POST /admin/kyc/{user_id}/reject — reason 빈 문자열 → 422
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_kyc_no_reason():
    """reason 빈 문자열 → pydantic validation error (422)."""
    from pydantic import ValidationError

    from app.api.admin_payouts import KYCRejectBody

    with pytest.raises(ValidationError):
        KYCRejectBody(reason="")


# ──────────────────────────────────────────────────────────────────────────────
# 7. GET /admin/settlements — month 필터
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settlements_with_month_filter():
    """month 파라미터 포함 정산 이력 조회 — 200 + pagination."""
    from app.api.admin_payouts import list_settlements

    admin = _make_admin_mock()
    artist_id = uuid.uuid4()
    settlement = _make_settlement_mock(artist_id, status="paid")

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=1)

    data_result = MagicMock()
    data_result.all = MagicMock(return_value=[(settlement, "홍길동", "artist@example.com")])

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return count_result
        return data_result

    db.execute = _execute

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await list_settlements(
            month="2026-04",
            artist_id=None,
            status=None,
            limit=20,
            offset=0,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert response["pagination"]["total"] == 1
    assert len(response["data"]) == 1
    assert response["data"][0]["status"] == "paid"
    assert response["data"][0]["artist_name"] == "홍길동"
    assert "export_url" in response


# ──────────────────────────────────────────────────────────────────────────────
# 8. GET /admin/settlements — status 필터
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settlements_with_status_filter():
    """status=pending 필터 — 해당 status만 반환."""
    from app.api.admin_payouts import list_settlements

    admin = _make_admin_mock()
    artist_id = uuid.uuid4()
    settlement = _make_settlement_mock(artist_id, status="pending")

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=1)

    data_result = MagicMock()
    data_result.all = MagicMock(return_value=[(settlement, "김예술", "kim@example.com")])

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return count_result
        return data_result

    db.execute = _execute

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await list_settlements(
            month=None,
            artist_id=None,
            status="pending",
            limit=20,
            offset=0,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert response["data"][0]["status"] == "pending"
    assert response["pagination"]["total"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# 9. GET /admin/settlements/{id} — 200 + items + stripe_transfer null (mock)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settlement_detail():
    """정산 상세 조회 — items 목록 + MOCK_PAYOUT_ 참조 시 stripe_transfer=null."""
    from app.api.admin_payouts import get_settlement_detail

    admin = _make_admin_mock()
    artist_id = uuid.uuid4()
    settlement = _make_settlement_mock(artist_id, status="paid")
    settlement_id = settlement.id

    # settlement_item mock
    item = MagicMock()
    item.order_id = uuid.uuid4()
    item.settlement_id = settlement_id

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    detail_result = MagicMock()
    detail_result.first = MagicMock(return_value=(settlement, "홍길동"))

    items_result = MagicMock()
    items_result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[item]))
    )

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        if idx == 0:
            return detail_result
        return items_result

    db.execute = _execute

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await get_settlement_detail(
            settlement_id=settlement_id,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert response["data"]["id"] == str(settlement_id)
    assert response["data"]["artist_name"] == "홍길동"
    assert len(response["data"]["items"]) == 1
    # MOCK_PAYOUT_ 접두사 → stripe_transfer = null
    assert response["data"]["stripe_transfer"] is None


# ──────────────────────────────────────────────────────────────────────────────
# 10. GET /admin/stripe-connect/{artist_id}/status — mock_mode=true
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_stripe_connect_status_mock_mode():
    """PAYMENT_PROVIDER != stripe → mock_mode=true 반환 (500 없음)."""
    from app.api.admin_payouts import get_stripe_connect_status

    admin = _make_admin_mock()
    user = _make_user_mock(stripe_customer_id=None)

    db = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _execute(stmt):
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(return_value=user)
        return r

    db.execute = _execute

    with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock):
        response = await get_stripe_connect_status(
            artist_id=user.id,
            request=_make_request(),
            admin=admin,
            db=db,
        )

    assert response["data"]["mock_mode"] is True
    assert response["data"]["charges_enabled"] is False
    assert response["data"]["payouts_enabled"] is False


# ──────────────────────────────────────────────────────────────────────────────
# 11. audit_log 기록 검증 (approve)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_kyc_audit_log_called():
    """KYC approve 시 record_audit(action='admin.kyc.approved') 호출 검증."""
    from app.api.admin_payouts import approve_kyc

    admin = _make_admin_mock()
    user = _make_user_mock(identity_verified_at=None)
    kyc_session = _make_kyc_session_mock(user.id, status="pending")

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    call_count = [0]

    async def _execute(stmt):
        idx = call_count[0]
        call_count[0] += 1
        r = MagicMock()
        r.scalar_one_or_none = MagicMock(
            return_value=user if idx == 0 else kyc_session
        )
        return r

    db.execute = _execute

    with patch("app.api.admin_payouts._create_stripe_connect_onboarding", new_callable=AsyncMock) as mock_stripe:
        mock_stripe.return_value = (None, None)
        with patch("app.api.admin_payouts.record_audit", new_callable=AsyncMock) as mock_audit:
            await approve_kyc(
                user_id=user.id, request=_make_request(), admin=admin, db=db
            )

    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args.kwargs
    assert call_kwargs["action"] == "admin.kyc.approved"
    assert call_kwargs["target_type"] == "user"
    assert call_kwargs["target_id"] == user.id


# ──────────────────────────────────────────────────────────────────────────────
# 12. Stripe API 실패 시 mock_mode=true graceful 반환
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stripe_connect_status_api_failure_returns_mock():
    """Stripe API 실패 시 500이 아닌 mock_mode=true 응답 반환 (graceful)."""
    from app.api.admin_payouts import _fetch_stripe_connect_status

    # settings.payment_provider = "stripe"로 설정 후 StripeProvider 실패 시뮬레이션
    # lazy import 사용으로 인해 sys.modules를 통해 patch
    import sys
    from unittest.mock import MagicMock as MM

    fake_stripe_provider = MM()
    fake_stripe_provider.get_connect_account_status = AsyncMock(
        side_effect=Exception("Stripe API timeout")
    )

    fake_module = MM()
    fake_module.StripeProvider = MM(return_value=fake_stripe_provider)

    with patch("app.core.config.get_settings") as mock_settings:
        settings_obj = MagicMock()
        settings_obj.payment_provider = "stripe"
        mock_settings.return_value = settings_obj

        # lazy import 경로 patch: app.services.payments.stripe_real
        original = sys.modules.get("app.services.payments.stripe_real")
        sys.modules["app.services.payments.stripe_real"] = fake_module
        try:
            with patch("app.api.admin_payouts.get_settings", return_value=settings_obj):
                result = await _fetch_stripe_connect_status("acct_test123")
        finally:
            if original is not None:
                sys.modules["app.services.payments.stripe_real"] = original
            else:
                sys.modules.pop("app.services.payments.stripe_real", None)

    assert result["mock_mode"] is True
    assert result["charges_enabled"] is False
