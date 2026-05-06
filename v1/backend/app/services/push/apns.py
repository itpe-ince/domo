"""APNs push service — B'-3 push-email-digest-foundation.

Sends push notifications to Apple Push Notification service (APNs)
via HTTP/2 + JWT authentication (aiohttp + PyJWT).

Mock mode: activates automatically when APNS_KEY_ID / APNS_TEAM_ID /
APNS_AUTH_KEY_P8 env vars are not set (or aiohttp not installed).
Console-logs delivery and returns success — no APNs calls made.

Usage:
    from app.services.push.apns import apns_service
    result = await apns_service.send(token, title, body, bundle_id="art.domo.app")
"""
from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)

try:
    import aiohttp  # type: ignore[import]
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False
    log.debug("aiohttp not installed — APNs will use Mock mode")

try:
    import jwt as pyjwt  # type: ignore[import]
    _PYJWT_AVAILABLE = True
except ImportError:
    _PYJWT_AVAILABLE = False
    log.debug("PyJWT not installed — APNs will use Mock mode")

_APNS_HOST_PROD = "api.push.apple.com"
_APNS_HOST_DEV = "api.sandbox.push.apple.com"
_APNS_PORT = 443


def _make_jwt(key_id: str, team_id: str, auth_key_p8: str) -> str:
    """Generate APNs JWT (ES256, 40-min validity)."""
    import time
    headers = {"alg": "ES256", "kid": key_id}
    payload = {"iss": team_id, "iat": int(time.time())}
    return pyjwt.encode(payload, auth_key_p8, algorithm="ES256", headers=headers)


class APNsService:
    """Async APNs push service with JWT authentication.

    Mock mode when credentials not configured or aiohttp/PyJWT absent.
    """

    def __init__(self) -> None:
        self._settings_loaded = False
        self._key_id: str = ""
        self._team_id: str = ""
        self._auth_key_p8: str = ""
        self._bundle_id: str = "art.domo.app"
        self._sandbox: bool = True

    def _load_settings(self) -> None:
        if self._settings_loaded:
            return
        self._settings_loaded = True
        from app.core.config import get_settings
        s = get_settings()
        self._key_id = getattr(s, "apns_key_id", "") or ""
        self._team_id = getattr(s, "apns_team_id", "") or ""
        self._auth_key_p8 = getattr(s, "apns_auth_key_p8", "") or ""
        self._bundle_id = getattr(s, "apns_bundle_id", "art.domo.app") or "art.domo.app"
        self._sandbox = getattr(s, "apns_sandbox", True)

    @property
    def is_mock(self) -> bool:
        self._load_settings()
        return (
            not self._key_id
            or not self._team_id
            or not self._auth_key_p8
            or not _AIOHTTP_AVAILABLE
            or not _PYJWT_AVAILABLE
        )

    async def send(
        self,
        token: str,
        title: str,
        body: str,
        bundle_id: str | None = None,
        badge: int | None = None,
    ) -> dict:
        """Send a single APNs notification. Returns result dict."""
        self._load_settings()

        if self.is_mock:
            return self._mock_send(token, title, body)

        host = _APNS_HOST_DEV if self._sandbox else _APNS_HOST_PROD
        url = f"https://{host}:{_APNS_PORT}/3/device/{token}"
        apns_topic = bundle_id or self._bundle_id

        jwt_token = _make_jwt(self._key_id, self._team_id, self._auth_key_p8)

        headers = {
            "authorization": f"bearer {jwt_token}",
            "apns-topic": apns_topic,
            "apns-push-type": "alert",
        }

        payload: dict = {
            "aps": {
                "alert": {"title": title, "body": body},
                "sound": "default",
            }
        }
        if badge is not None:
            payload["aps"]["badge"] = badge

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        apns_id = resp.headers.get("apns-id", "")
                        return {"message_id": apns_id, "status": "sent", "platform": "apns"}
                    reason = await resp.text()
                    log.warning(
                        "APNs send failed: status=%d reason=%s token=%s",
                        resp.status,
                        reason,
                        token[:20],
                    )
                    return {
                        "message_id": None,
                        "status": "error",
                        "error": reason,
                        "http_status": resp.status,
                        "platform": "apns",
                    }
        except Exception as exc:
            log.exception("APNs: send failed token=%s", token[:20])
            return {"message_id": None, "status": "error", "error": str(exc), "platform": "apns"}

    def _mock_send(self, token: str, title: str, body: str) -> dict:
        mock_id = f"apns-mock-{uuid.uuid4().hex[:12]}"
        log.info(
            "APNs MOCK send | token=%s... title=%r body=%r message_id=%s",
            token[:20],
            title,
            body,
            mock_id,
        )
        return {"message_id": mock_id, "status": "mock", "platform": "apns"}

    async def send_batch(
        self,
        tokens: list[str],
        title: str,
        body: str,
        bundle_id: str | None = None,
    ) -> list[dict]:
        """Send to multiple APNs tokens. Returns per-token result list."""
        results = []
        for token in tokens:
            result = await self.send(token, title, body, bundle_id=bundle_id)
            results.append(result)
        return results


# Module-level singleton
apns_service = APNsService()
