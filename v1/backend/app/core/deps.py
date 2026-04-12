import uuid

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError("UNAUTHORIZED", "Missing bearer token", http_status=401)

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise ApiError("UNAUTHORIZED", str(e), http_status=401) from e

    if payload.get("type") != "access":
        raise ApiError("UNAUTHORIZED", "Wrong token type", http_status=401)

    user_id = payload.get("sub")
    if not user_id:
        raise ApiError("UNAUTHORIZED", "Invalid token payload", http_status=401)

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise ApiError("NOT_FOUND", "User not found", http_status=404)

    if user.status == "suspended":
        raise ApiError("ACCOUNT_SUSPENDED", "Account suspended", http_status=403)

    return user


async def require_active_user(user: User = Depends(get_current_user)) -> User:
    if user.status != "active":
        raise ApiError("ACCOUNT_SUSPENDED", "Account not active", http_status=403)
    return user
