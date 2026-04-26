"""WebAuthn / Passkey for admin accounts.

Flow A — Registration (admin must already be authenticated):
    POST /auth/admin/webauthn/register/begin   {nickname?}
        → {challenge_token, options: PublicKeyCredentialCreationOptions}
    POST /auth/admin/webauthn/register/finish  {challenge_token, credential}
        → {credential_id, nickname}

Flow B — Authentication (replaces TOTP step entirely):
    POST /auth/admin/webauthn/authenticate/begin   {email}
        → {challenge_token, options: PublicKeyCredentialRequestOptions}
    POST /auth/admin/webauthn/authenticate/finish  {challenge_token, assertion}
        → {tokens, user}

Management:
    GET    /auth/admin/webauthn/credentials           → list registered authenticators
    DELETE /auth/admin/webauthn/credentials/{id}      → revoke

Storage: short-lived challenges in webauthn_challenges (5 min TTL).
        Long-lived credentials in webauthn_credentials (per-user N).
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import ApiError
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.models.webauthn import WebauthnChallenge, WebauthnCredential
from app.schemas.auth import TokenPair, UserPublic
from app.services.auth_tokens import issue_initial_tokens

router = APIRouter(prefix="/auth/admin/webauthn", tags=["admin-webauthn"])
log = logging.getLogger(__name__)
settings = get_settings()

_CHALLENGE_TTL = timedelta(minutes=5)


# ─── helpers ───────────────────────────────────────────────────────────
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = 4 - (len(s) % 4)
    if pad and pad < 4:
        s = s + "=" * pad
    return base64.urlsafe_b64decode(s)


def _client_info(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


async def _store_challenge(
    db: AsyncSession,
    challenge: bytes,
    purpose: str,
    user_id: UUID | None = None,
    expected_email: str | None = None,
) -> str:
    """Persist a challenge and return the opaque token (challenge id) the
    client echoes back to bind the begin/finish pair."""
    row = WebauthnChallenge(
        challenge=challenge,
        purpose=purpose,
        user_id=user_id,
        expected_email=expected_email,
        expires_at=datetime.now(timezone.utc) + _CHALLENGE_TTL,
    )
    db.add(row)
    await db.flush()
    return str(row.id)


async def _consume_challenge(
    db: AsyncSession, challenge_token: str, purpose: str
) -> WebauthnChallenge:
    """Look up a challenge by token, validate purpose+expiry, and DELETE
    it so it can never be replayed. Caller is responsible for commit."""
    try:
        challenge_id = UUID(challenge_token)
    except (ValueError, TypeError) as e:
        raise ApiError(
            "INVALID_CHALLENGE", "Invalid challenge token.", http_status=400
        ) from e
    result = await db.execute(
        select(WebauthnChallenge).where(WebauthnChallenge.id == challenge_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise ApiError(
            "INVALID_CHALLENGE", "Challenge not found.", http_status=400
        )
    if row.purpose != purpose:
        raise ApiError(
            "INVALID_CHALLENGE", "Challenge purpose mismatch.", http_status=400
        )
    if row.expires_at < datetime.now(timezone.utc):
        await db.execute(
            delete(WebauthnChallenge).where(WebauthnChallenge.id == row.id)
        )
        raise ApiError(
            "INVALID_CHALLENGE", "Challenge expired.", http_status=400
        )
    # Snapshot before deleting
    snapshot = WebauthnChallenge(
        id=row.id,
        challenge=row.challenge,
        purpose=row.purpose,
        user_id=row.user_id,
        expected_email=row.expected_email,
        expires_at=row.expires_at,
    )
    await db.execute(
        delete(WebauthnChallenge).where(WebauthnChallenge.id == row.id)
    )
    return snapshot


# ─── Schemas ───────────────────────────────────────────────────────────
class RegisterBeginRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=100)


class RegisterFinishRequest(BaseModel):
    challenge_token: str
    credential: dict
    nickname: str | None = Field(default=None, max_length=100)


class AuthenticateBeginRequest(BaseModel):
    email: EmailStr


class AuthenticateFinishRequest(BaseModel):
    challenge_token: str
    assertion: dict


# ─── Registration: begin ───────────────────────────────────────────────
@router.post("/register/begin")
async def register_begin(
    body: RegisterBeginRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)

    # Exclude existing credentials so the authenticator does not re-enroll
    existing = await db.execute(
        select(WebauthnCredential).where(WebauthnCredential.user_id == user.id)
    )
    exclude = [
        PublicKeyCredentialDescriptor(id=c.credential_id)
        for c in existing.scalars().all()
    ]

    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.webauthn_rp_name,
        user_id=str(user.id).encode("utf-8"),
        user_name=user.email,
        user_display_name=user.display_name or user.email,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
    )

    challenge_token = await _store_challenge(
        db, options.challenge, purpose="registration", user_id=user.id
    )
    await db.commit()

    return {
        "data": {
            "challenge_token": challenge_token,
            "options": options_to_json(options),
        }
    }


# ─── Registration: finish ──────────────────────────────────────────────
@router.post("/register/finish")
async def register_finish(
    body: RegisterFinishRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)

    challenge_row = await _consume_challenge(
        db, body.challenge_token, purpose="registration"
    )
    if challenge_row.user_id != user.id:
        raise ApiError(
            "INVALID_CHALLENGE", "Challenge does not belong to this user.", http_status=400
        )

    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=challenge_row.challenge,
            expected_origin=settings.webauthn_rp_origin,
            expected_rp_id=settings.webauthn_rp_id,
            require_user_verification=False,
        )
    except InvalidRegistrationResponse as e:
        raise ApiError(
            "WEBAUTHN_REGISTRATION_FAILED",
            f"Registration verification failed: {e}",
            http_status=400,
        ) from e

    # Persist the credential
    transports = body.credential.get("response", {}).get("transports") or None
    if isinstance(transports, list):
        transports = ",".join(transports)[:100]

    cred = WebauthnCredential(
        user_id=user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        transports=transports,
        nickname=body.nickname or "Authenticator",
        aaguid=getattr(verification, "aaguid", None),
        backed_up=bool(getattr(verification, "credential_backed_up", False)),
    )
    db.add(cred)
    await db.commit()

    return {
        "data": {
            "id": str(cred.id),
            "credential_id": _b64url(cred.credential_id),
            "nickname": cred.nickname,
        }
    }


# ─── Authentication: begin ─────────────────────────────────────────────
@router.post("/authenticate/begin")
async def authenticate_begin(
    body: AuthenticateBeginRequest,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    """Issue a challenge for an admin to sign with their passkey.

    We reveal whether the email exists by including their credential IDs
    (allow_credentials). To minimize enumeration, we still issue a
    challenge for non-admin / nonexistent emails but with no credentials,
    making the response shape constant. The verify step will fail.
    """
    email = body.email.lower()
    result = await db.execute(
        select(User).where(User.email == email, User.role == "admin")
    )
    user = result.scalar_one_or_none()

    allow_credentials: list[PublicKeyCredentialDescriptor] = []
    if user and user.status == "active":
        creds = await db.execute(
            select(WebauthnCredential).where(WebauthnCredential.user_id == user.id)
        )
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=c.credential_id)
            for c in creds.scalars().all()
        ]

    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=allow_credentials or None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    challenge_token = await _store_challenge(
        db,
        options.challenge,
        purpose="authentication",
        user_id=user.id if user else None,
        expected_email=email,
    )
    await db.commit()

    return {
        "data": {
            "challenge_token": challenge_token,
            "options": options_to_json(options),
        }
    }


# ─── Authentication: finish ────────────────────────────────────────────
@router.post("/authenticate/finish")
async def authenticate_finish(
    body: AuthenticateFinishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=rate_limit("auth_login"),
):
    challenge_row = await _consume_challenge(
        db, body.challenge_token, purpose="authentication"
    )

    # Recover the credential row by credential_id from the assertion
    raw_cred_id_b64 = body.assertion.get("rawId") or body.assertion.get("id") or ""
    try:
        raw_cred_id = _b64url_decode(raw_cred_id_b64)
    except Exception as e:  # noqa: BLE001
        raise ApiError(
            "INVALID_ASSERTION", "Malformed credential ID.", http_status=400
        ) from e

    cred_result = await db.execute(
        select(WebauthnCredential).where(
            WebauthnCredential.credential_id == raw_cred_id
        )
    )
    cred = cred_result.scalar_one_or_none()
    if not cred:
        raise ApiError(
            "INVALID_ASSERTION", "Unknown credential.", http_status=401
        )
    # Ensure the resolved credential matches the challenge's expected user
    if challenge_row.user_id and challenge_row.user_id != cred.user_id:
        raise ApiError(
            "INVALID_ASSERTION", "Credential does not match challenge.", http_status=401
        )

    user_result = await db.execute(select(User).where(User.id == cred.user_id))
    user = user_result.scalar_one_or_none()
    if not user or user.role != "admin" or user.status != "active":
        raise ApiError(
            "INVALID_ASSERTION", "Account not available.", http_status=401
        )

    try:
        verification = verify_authentication_response(
            credential=body.assertion,
            expected_challenge=challenge_row.challenge,
            expected_origin=settings.webauthn_rp_origin,
            expected_rp_id=settings.webauthn_rp_id,
            credential_public_key=cred.public_key,
            credential_current_sign_count=cred.sign_count,
            require_user_verification=False,
        )
    except InvalidAuthenticationResponse as e:
        raise ApiError(
            "INVALID_ASSERTION",
            f"Assertion verification failed: {e}",
            http_status=401,
        ) from e

    ua, ip = _client_info(request)
    cred.sign_count = verification.new_sign_count
    cred.last_used_at = datetime.now(timezone.utc)
    cred.last_used_user_agent = ua

    access, refresh = await issue_initial_tokens(
        db, user, user_agent=ua, ip_address=ip
    )
    await db.commit()

    return {
        "data": {
            "tokens": TokenPair(
                access_token=access, refresh_token=refresh
            ).model_dump(),
            "user": UserPublic.model_validate(user).model_dump(mode="json"),
            "auth_method": "webauthn",
        }
    }


# ─── Management ────────────────────────────────────────────────────────
@router.get("/credentials")
async def list_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    result = await db.execute(
        select(WebauthnCredential)
        .where(WebauthnCredential.user_id == user.id)
        .order_by(WebauthnCredential.created_at.desc())
    )
    creds = result.scalars().all()
    return {
        "data": [
            {
                "id": str(c.id),
                "credential_id": _b64url(c.credential_id),
                "nickname": c.nickname,
                "transports": c.transports,
                "backed_up": c.backed_up,
                "created_at": c.created_at.isoformat(),
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            }
            for c in creds
        ]
    }


@router.delete("/credentials/{credential_id}")
async def revoke_credential(
    credential_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "admin":
        raise ApiError("FORBIDDEN", "Admin only.", http_status=403)
    result = await db.execute(
        select(WebauthnCredential).where(
            WebauthnCredential.id == credential_id,
            WebauthnCredential.user_id == user.id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise ApiError("NOT_FOUND", "Credential not found.", http_status=404)
    await db.execute(
        delete(WebauthnCredential).where(WebauthnCredential.id == credential_id)
    )
    await db.commit()
    return {"data": {"ok": True}}
