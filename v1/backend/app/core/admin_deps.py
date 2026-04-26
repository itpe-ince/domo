from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_db
from app.models.user import User
from app.models.webauthn import WebauthnCredential


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Role-only check. Use this ONLY on endpoints that admins must reach
    BEFORE second-factor enrollment is complete (e.g. TOTP setup, Passkey
    register). All other admin endpoints should use `require_admin_with_2fa`."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin role required", http_status=403)
    return user


async def require_admin_with_2fa(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Role + at-least-one second factor enrolled.

    First-time admin (password set, but neither TOTP nor any Passkey
    registered) is rejected with 403 SECOND_FACTOR_REQUIRED. The frontend
    must redirect such users to /settings/totp-setup or /settings/passkeys
    BEFORE letting them reach business endpoints.

    This is the gate that makes URL-bar bypass impossible — the client
    can navigate freely but the API will refuse every protected route."""
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin role required", http_status=403)
    if user.totp_enabled_at is not None:
        return user
    # Fall back to checking for any registered Passkey
    result = await db.execute(
        select(func.count(WebauthnCredential.id)).where(
            WebauthnCredential.user_id == user.id
        )
    )
    if int(result.scalar_one() or 0) > 0:
        return user
    raise ApiError(
        "SECOND_FACTOR_REQUIRED",
        "TOTP or Passkey enrollment required before accessing this resource.",
        http_status=403,
        details={"setup_url": "/settings/totp-setup"},
    )
