from fastapi import Depends

from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.models.user import User


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin role required", http_status=403)
    return user
