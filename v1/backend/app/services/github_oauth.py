"""GitHub OAuth 헬퍼 서비스 — Phase 12 C-2.

code → access_token 교환, GitHub API 사용자/이메일 조회.
GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET 미설정 시 ApiError 발생.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import get_settings
from app.core.errors import ApiError

log = logging.getLogger(__name__)

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"


def _check_github_configured() -> None:
    """GitHub OAuth 환경변수 미설정 시 503 반환."""
    s = get_settings()
    if not s.github_client_id or not s.github_client_secret:
        raise ApiError(
            "GITHUB_OAUTH_DISABLED",
            "GitHub OAuth가 서버에 설정되지 않았습니다.",
            http_status=503,
        )


async def exchange_github_code(code: str, redirect_uri: str) -> str:
    """GitHub OAuth authorization code → access_token 교환.

    Args:
        code: 프론트엔드에서 전달한 OAuth code
        redirect_uri: GitHub App에 등록된 redirect URI

    Returns:
        GitHub access_token 문자열

    Raises:
        ApiError: code 교환 실패 또는 GitHub API 오류
    """
    _check_github_configured()
    s = get_settings()

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": s.github_client_id,
                    "client_secret": s.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            log.warning("github_token_exchange_http_error | status=%s", exc.response.status_code)
            raise ApiError(
                "GITHUB_TOKEN_EXCHANGE_FAILED",
                "GitHub 서버 통신 오류가 발생했습니다.",
                http_status=502,
            ) from exc
        except httpx.TimeoutException:
            raise ApiError(
                "GITHUB_TOKEN_EXCHANGE_FAILED",
                "GitHub 서버 응답 시간 초과.",
                http_status=504,
            )

        data = resp.json()
        if "error" in data:
            raise ApiError(
                "GITHUB_TOKEN_EXCHANGE_FAILED",
                data.get("error_description", "GitHub code 교환에 실패했습니다."),
                http_status=400,
            )

        access_token = data.get("access_token")
        if not access_token:
            raise ApiError(
                "GITHUB_TOKEN_EXCHANGE_FAILED",
                "GitHub access_token을 받지 못했습니다.",
                http_status=400,
            )
        return access_token


async def fetch_github_user(access_token: str) -> dict:
    """GitHub /user API 조회.

    Returns:
        GitHub 사용자 정보 dict (id, login, name, avatar_url 등)
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ApiError(
                "GITHUB_API_ERROR",
                "GitHub 사용자 정보 조회 실패.",
                http_status=502,
            ) from exc
        return resp.json()


async def fetch_github_primary_email(access_token: str) -> str | None:
    """GitHub /user/emails에서 primary + verified 이메일 반환.

    Returns:
        primary verified 이메일 주소, 없으면 None
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{GITHUB_API_BASE}/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            return None

        emails = resp.json()
        if not isinstance(emails, list):
            return None

        for entry in emails:
            if entry.get("primary") and entry.get("verified"):
                return entry.get("email")
        return None
