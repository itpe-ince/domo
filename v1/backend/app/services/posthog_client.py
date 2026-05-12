"""PostHog server-side 클라이언트 — Phase 10 K-8.

posthog-python SDK 통합 (pip install posthog).
POSTHOG_API_KEY 미설정 시 Mock 모드로 동작:
  - get_feature_flag() → False 반환 (전 사용자 v1)
  - capture() → log.debug만 출력, PostHog 미발화

posthog 라이브러리 미설치 시에도 graceful 동작:
  - ImportError catch → Mock 모드로 자동 전환 + WARNING 로그
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY", "")
_POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://app.posthog.com")
_MOCK_MODE = not bool(_POSTHOG_API_KEY)

_posthog_instance = None


def _get_posthog():
    """posthog 인스턴스 lazy 초기화 (import 실패 시 None)."""
    global _posthog_instance
    if _posthog_instance is not None:
        return _posthog_instance
    if _MOCK_MODE:
        return None
    try:
        import posthog as ph  # type: ignore[import]
        ph.api_key = _POSTHOG_API_KEY
        ph.host = _POSTHOG_HOST
        _posthog_instance = ph
        log.info("PostHog client 초기화 완료 (host=%s)", _POSTHOG_HOST)
        return ph
    except ImportError:
        log.warning(
            "posthog-python 미설치 — Mock 모드로 전환. "
            "설치: pip install posthog"
        )
        return None


class _PostHogClient:
    """PostHog 클라이언트 래퍼 (Mock 모드 포함)."""

    async def get_feature_flag(self, flag_key: str, user_id: str) -> bool:
        """PostHog feature flag 조회.

        반환: True(v2 treatment) / False(v1 control)
        Mock 모드: False 반환 + WARNING 로그
        """
        ph = _get_posthog()
        if ph is None:
            if _MOCK_MODE:
                log.warning(
                    "PostHog Mock: get_feature_flag('%s', user=%s) → False "
                    "(POSTHOG_API_KEY 미설정)",
                    flag_key, user_id,
                )
            else:
                # posthog 라이브러리 미설치
                log.warning(
                    "PostHog Mock: get_feature_flag('%s', user=%s) → False "
                    "(posthog-python 미설치)",
                    flag_key, user_id,
                )
            return False
        try:
            result = ph.get_feature_flag(flag_key, user_id)
            enabled = bool(result)
            log.debug(
                "PostHog flag '%s' user=%s → %s",
                flag_key, user_id, "v2" if enabled else "v1",
            )
            return enabled
        except Exception as exc:  # noqa: BLE001
            log.warning("PostHog get_feature_flag 실패 (%s) → False", exc)
            return False

    async def capture(
        self,
        event_name: str,
        user_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """PostHog 이벤트 발화.

        Mock 모드: log.debug만 출력.
        """
        ph = _get_posthog()
        if ph is None:
            log.debug(
                "PostHog Mock: capture event='%s' user=%s props=%s",
                event_name, user_id, properties,
            )
            return
        try:
            ph.capture(
                distinct_id=user_id,
                event=event_name,
                properties=properties or {},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("PostHog capture 실패 (event=%s): %s", event_name, exc)


# 모듈 레벨 싱글톤 클라이언트
posthog_client = _PostHogClient()
