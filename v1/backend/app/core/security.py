import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)

# Bcrypt 72-byte hard limit. We enforce at the call site and reject longer
# passwords explicitly rather than silently truncating (which would let
# different long passwords collide on the same hash).
_BCRYPT_MAX_BYTES = 72


def create_access_token(subject: str, role: str, status: str = "active") -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "status": status,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


# ─── Admin password (bcrypt — direct, no passlib) ──────────────────────
def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt (cost=12). Raises ValueError
    if the password exceeds bcrypt's 72-byte limit — caller must reject
    rather than silently truncate."""
    pw_bytes = plain.encode("utf-8")
    if len(pw_bytes) > _BCRYPT_MAX_BYTES:
        raise ValueError(
            f"Password exceeds bcrypt's {_BCRYPT_MAX_BYTES}-byte limit "
            f"(got {len(pw_bytes)} bytes). Use a shorter password."
        )
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt verification. Returns False on any error
    (malformed hash, encoding issue, etc.) to avoid leaking info."""
    try:
        pw_bytes = plain.encode("utf-8")
        if len(pw_bytes) > _BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── Admin recovery codes (one-time backup) ────────────────────────────
# Format: "XXXX-XXXX-XXXX" (12 chars + 2 dashes), Crockford base32 alphabet
# (no I, L, O, U) for unambiguous transcription. ~60 bits entropy.
_RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"


def generate_recovery_codes(count: int = 10) -> list[str]:
    """Generate `count` plaintext one-time recovery codes. Caller must
    show these to the user once and store only the bcrypt hashes."""
    out: list[str] = []
    for _ in range(count):
        groups = [
            "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(4))
            for _ in range(3)
        ]
        out.append("-".join(groups))
    return out


def hash_recovery_code(plain: str) -> str:
    """Bcrypt-hash a recovery code. Codes are short (14 bytes) so safe."""
    return hash_password(_normalize_recovery_code(plain))


def verify_recovery_code(plain: str, hashed: str) -> bool:
    """Constant-time recovery code verification with normalization."""
    return verify_password(_normalize_recovery_code(plain), hashed)


def _normalize_recovery_code(code: str) -> str:
    """Strip dashes/whitespace and uppercase. Lets the user type the code
    in any case / with or without dashes / with stray spaces."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


# ─── Admin TOTP (RFC 6238) ──────────────────────────────────────────────
def generate_totp_secret() -> str:
    """Generate a base32 TOTP secret (160 bits, RFC 4226 §5.4)."""
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, account_name: str, issuer: str = "Domo Admin") -> str:
    """otpauth://-style URI for QR code (Google Authenticator / Authy)."""
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code. valid_window=1 allows ±30s drift.
    Accepts either a plaintext base32 secret OR an encrypted blob (auto-detect)."""
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    plain = decrypt_totp_secret(secret)
    return pyotp.TOTP(plain).verify(code, valid_window=valid_window)


# ─── TOTP secret at-rest encryption (Fernet AES-128-CBC + HMAC-SHA256) ──
# Secrets stored in DB are prefixed with "fernet:" when encrypted, or stored
# plain (legacy/dev) otherwise. encrypt/decrypt auto-handle both formats so
# rotation can be done lazily.
_FERNET_PREFIX = "fernet:"
_fernet_singleton: Fernet | None = None


def _get_fernet() -> Fernet | None:
    """Lazy-load the Fernet cipher from settings. Returns None if no key
    is configured (dev fallback — secrets stored plaintext with warning)."""
    global _fernet_singleton
    if _fernet_singleton is not None:
        return _fernet_singleton
    key = settings.totp_encryption_key.strip()
    if not key:
        log.warning(
            "TOTP_ENCRYPTION_KEY is not set — admin TOTP secrets will be "
            "stored in PLAINTEXT. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
        return None
    try:
        _fernet_singleton = Fernet(key.encode("utf-8"))
        return _fernet_singleton
    except (ValueError, TypeError) as e:
        log.error("Invalid TOTP_ENCRYPTION_KEY (must be URL-safe base64 32-byte key): %s", e)
        return None


def encrypt_totp_secret(plain: str) -> str:
    """Encrypt a TOTP secret for at-rest storage. Returns ciphertext with
    prefix; if no encryption key configured, returns plaintext as-is."""
    if not plain:
        return plain
    cipher = _get_fernet()
    if cipher is None:
        return plain
    token = cipher.encrypt(plain.encode("utf-8")).decode("utf-8")
    return _FERNET_PREFIX + token


def decrypt_totp_secret(stored: str) -> str:
    """Decrypt a stored TOTP secret. Auto-detects ciphertext vs plaintext
    by prefix so legacy rows continue to work during rotation."""
    if not stored:
        return stored
    if not stored.startswith(_FERNET_PREFIX):
        return stored  # legacy plaintext
    cipher = _get_fernet()
    if cipher is None:
        # Should not happen — we only emit prefix when key existed at write
        raise RuntimeError(
            "Encrypted TOTP secret found but TOTP_ENCRYPTION_KEY is not set."
        )
    try:
        return cipher.decrypt(stored[len(_FERNET_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("TOTP secret decryption failed (key rotated?)") from e


# ─── Admin step-up token (short-lived, password-pass → TOTP-pending) ───
def create_admin_challenge_token(user_id: str) -> str:
    """5-minute token issued after password verification, used to prove
    a TOTP-step request belongs to the same login flow."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "type": "admin_challenge",
        "nonce": secrets.token_urlsafe(8),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_admin_challenge_token(token: str) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "admin_challenge":
        raise ValueError("Not an admin challenge token")
    return payload
