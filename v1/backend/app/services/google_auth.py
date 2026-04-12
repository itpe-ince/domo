from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import get_settings
from app.core.errors import ApiError

settings = get_settings()


async def verify_google_id_token(token: str) -> dict[str, Any]:
    """
    Verify a Google ID token and return user info.
    Returns: { "sub", "email", "name", "picture", ... }

    Phase 0: Real verification when GOOGLE_CLIENT_ID is configured.
    If not configured, falls back to a mock for local dev convenience.
    """
    if not settings.google_client_id:
        # Local dev fallback: accept "mock:<email>" format for testing
        if token.startswith("mock:"):
            email = token.split(":", 1)[1]
            return {
                "sub": f"mock-{email}",
                "email": email,
                "name": email.split("@")[0],
                "picture": None,
            }
        raise ApiError(
            "INVALID_REQUEST",
            "GOOGLE_CLIENT_ID not configured. Use mock:<email> in dev.",
            http_status=400,
        )

    try:
        info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.google_client_id,
        )
        return info
    except ValueError as e:
        raise ApiError("UNAUTHORIZED", f"Invalid Google token: {e}", http_status=401) from e
