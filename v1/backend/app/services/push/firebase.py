"""FCM push service — B'-3 push-email-digest-foundation.

Sends push notifications via Firebase Cloud Messaging (firebase-admin SDK).

Mock mode: activates automatically when FIREBASE_CREDENTIALS_JSON env var is
not set (or firebase-admin not installed). Console-logs delivery and returns
success — no actual FCM calls made.

Usage:
    from app.services.push.firebase import fcm_service
    result = await fcm_service.send(token, title, body, data={"link": "/me"})
"""
from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)

try:
    import firebase_admin  # type: ignore[import]
    from firebase_admin import credentials, messaging  # type: ignore[import]
    _FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    _FIREBASE_ADMIN_AVAILABLE = False
    log.debug("firebase-admin not installed — FCM will use Mock mode")


class FCMService:
    """Thin async-compatible wrapper around firebase_admin.messaging.

    All public methods are async (non-blocking via thread executor for SDK calls).
    Mock mode: credentials JSON not configured or SDK not installed.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._app: object | None = None

    def _load(self) -> None:
        """Lazy init firebase_admin app from settings."""
        if self._initialized:
            return
        self._initialized = True
        if not _FIREBASE_ADMIN_AVAILABLE:
            return

        from app.core.config import get_settings
        s = get_settings()
        creds_json = getattr(s, "firebase_credentials_json", "") or ""
        if not creds_json:
            return

        try:
            import json
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
            # Only init if not already initialized (test isolation)
            if not firebase_admin._apps:  # type: ignore[attr-defined]
                self._app = firebase_admin.initialize_app(cred)
            else:
                self._app = firebase_admin.get_app()
        except Exception:
            log.exception("FCM: failed to initialize firebase_admin app — using Mock mode")
            self._app = None

    @property
    def is_mock(self) -> bool:
        self._load()
        return self._app is None or not _FIREBASE_ADMIN_AVAILABLE

    async def send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Send a single FCM message. Returns result dict."""
        self._load()

        if self.is_mock:
            return self._mock_send(token, title, body)

        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_sync, token, title, body, data)

    def _send_sync(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict:
        """Synchronous FCM send (runs in thread executor)."""
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        try:
            message_id = messaging.send(message)
            return {"message_id": message_id, "status": "sent", "platform": "fcm"}
        except messaging.UnregisteredError:
            log.warning("FCM: token unregistered — token=%s", token[:20])
            return {"message_id": None, "status": "unregistered", "platform": "fcm"}
        except Exception as exc:
            log.exception("FCM: send failed token=%s", token[:20])
            return {"message_id": None, "status": "error", "error": str(exc), "platform": "fcm"}

    def _mock_send(self, token: str, title: str, body: str) -> dict:
        mock_id = f"fcm-mock-{uuid.uuid4().hex[:12]}"
        log.info(
            "FCM MOCK send | token=%s... title=%r body=%r message_id=%s",
            token[:20],
            title,
            body,
            mock_id,
        )
        return {"message_id": mock_id, "status": "mock", "platform": "fcm"}

    async def send_batch(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> list[dict]:
        """Send to multiple FCM tokens. Returns per-token result list."""
        results = []
        for token in tokens:
            result = await self.send(token, title, body, data=data)
            results.append(result)
        return results


# Module-level singleton
fcm_service = FCMService()
