"""Unified push notification dispatcher — B'-3 push-email-digest-foundation.

Routes push notifications to FCM (Android/Web) or APNs (iOS) based on token platform.
Respects per-user NotificationPreferences (push_enabled + push_per_type).

Usage:
    from app.services.push_notifier import push_notifier
    results = await push_notifier.notify_user(
        db, user_id, notification_type="auction", title="...", body="..."
    )
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Type categories for preference lookup
_TYPE_TO_CATEGORY: dict[str, str] = {
    "auction_ending_24h": "auction",
    "auction_ending_6h": "auction",
    "auction_ending_1h": "auction",
    "auction_ended": "auction",
    "auction_outbid": "auction",
    "auction_won": "auction",
    "auction_lost": "auction",
    "sponsor_received": "sponsorship",
    "sponsor_milestone": "sponsorship",
    "subscription_new": "sponsorship",
    "subscription_cancelled": "sponsorship",
    "subscription_expiring": "sponsorship",
    "like": "engagement",
    "comment": "engagement",
    "reply": "engagement",
    "follow": "engagement",
    "mention": "engagement",
    "system": "system",
    "announcement": "system",
    "artist_approved": "system",
    "artist_rejected": "system",
    "warning_issued": "system",
    "tier_release": "system",
    "email_digest": "digest",
}


def _category_for(notification_type: str) -> str:
    return _TYPE_TO_CATEGORY.get(notification_type, "system")


class PushNotifier:
    """Dispatch push notifications respecting user preferences.

    Imports FCM/APNs services lazily to avoid circular dependencies and to
    ensure Mock mode is respected when running in CI without credentials.
    """

    async def _is_push_enabled(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
    ) -> bool:
        """Check if push is enabled for the user + type combination.

        Returns False (opt-out) when NotificationPreferences row is absent.
        GDPR default: False.
        """
        from app.models.notification_preferences import NotificationPreferences
        result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()
        if prefs is None:
            return False  # GDPR default: not opted in

        if not prefs.push_enabled:
            return False

        # Per-type override: if key exists in JSONB, it takes precedence
        category = _category_for(notification_type)
        per_type: dict = prefs.push_per_type or {}
        if category in per_type:
            return bool(per_type[category])

        return prefs.push_enabled

    async def notify_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> list[dict]:
        """Send push notification to all active devices of a user.

        Returns list of per-device result dicts (empty list if no active tokens
        or push not enabled).
        """
        from app.models.device_token import DeviceToken
        from app.services.push.firebase import fcm_service
        from app.services.push.apns import apns_service

        # Check preferences first (GDPR gate)
        enabled = await self._is_push_enabled(db, user_id, notification_type)
        if not enabled:
            log.debug(
                "push_notifier: user %s push disabled for type=%s — skipping",
                user_id,
                notification_type,
            )
            return []

        # Fetch active device tokens
        result = await db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.deleted_at.is_(None),
                )
            )
        )
        tokens = list(result.scalars().all())

        if not tokens:
            log.debug("push_notifier: no active tokens for user=%s", user_id)
            return []

        results: list[dict] = []
        now = datetime.now(timezone.utc)

        for device in tokens:
            try:
                if device.platform == "fcm":
                    result_dict = await fcm_service.send(
                        device.token, title, body, data=data
                    )
                elif device.platform == "apns":
                    result_dict = await apns_service.send(
                        device.token, title, body
                    )
                else:
                    log.warning(
                        "push_notifier: unknown platform=%s for token id=%s",
                        device.platform,
                        device.id,
                    )
                    continue

                if result_dict.get("status") in ("sent", "mock"):
                    device.last_active_at = now
                elif result_dict.get("status") == "unregistered":
                    # Soft-delete stale token
                    device.deleted_at = now
                    log.info(
                        "push_notifier: token soft-deleted (unregistered) id=%s user=%s",
                        device.id,
                        user_id,
                    )

                results.append(result_dict)

            except Exception:
                log.exception(
                    "push_notifier: unexpected error for device id=%s user=%s",
                    device.id,
                    user_id,
                )

        if results:
            await db.commit()

        return results

    async def notify_many(
        self,
        db: AsyncSession,
        user_ids: list[uuid.UUID],
        notification_type: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> dict[str, list[dict]]:
        """Send push to multiple users. Returns {user_id_str: results} map."""
        all_results: dict[str, list[dict]] = {}
        for uid in user_ids:
            all_results[str(uid)] = await self.notify_user(
                db, uid, notification_type, title, body, data=data
            )
        return all_results


# Module-level singleton
push_notifier = PushNotifier()
