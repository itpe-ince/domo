"""WebAuthn / Passkey credential storage for admin users.

A user can have multiple credentials (e.g. Mac TouchID + iPhone FaceID).
Each row is one registered authenticator.
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebauthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The authenticator's credential ID (binary, base64url-encoded when sent
    # to the client). Unique across all users.
    credential_id: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False, unique=True
    )
    # COSE-encoded public key, used to verify assertion signatures.
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Replay-prevention counter — must monotonically increase per signature.
    sign_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    # Authenticator transports hint for UI (usb, nfc, ble, internal, hybrid)
    transports: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Friendly label admin sets ("MacBook TouchID", "YubiKey 5C")
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # AAGUID identifies the authenticator make/model (16 bytes)
    aaguid: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    # Optional: stored backup state flag (passkey synced across devices)
    backed_up: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)


class WebauthnChallenge(Base):
    """Short-lived challenges issued during registration / authentication.

    The challenge is bound to a session by either user_id (registration —
    must be authenticated) OR challenge_token (authentication — pre-login,
    we issue a one-time token and require the client to echo it back). A
    background sweep deletes rows older than 5 minutes."""

    __tablename__ = "webauthn_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)
    # 'registration' | 'authentication'
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # For pre-login (authentication) we also accept email→user lookup
    expected_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
