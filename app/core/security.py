"""Security utilities: JWT creation/verification and password hashing."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of *plain* password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

TokenType = Literal["access", "refresh"]


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    """Internal helper that builds a signed JWT.

    A random `jti` (JWT ID) is included so two tokens issued for the same
    user in the same second always produce different hashes.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": generate_jti(),   # unique per token — prevents hash collisions
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(user_id: str) -> str:
    """Return a short-lived access JWT for *user_id*."""
    return _create_token(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Return (raw_refresh_token, token_hash).

    The raw token is sent to the client; only the hash is persisted in DB.
    SHA-256 is sufficient here — the raw token is already high-entropy (JWT).
    """
    raw = _create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )
    token_hash = _hash_token(raw)
    return raw, token_hash


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises JWTError on any failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


# ---------------------------------------------------------------------------
# Refresh-token hashing (for DB storage)
# ---------------------------------------------------------------------------

def _hash_token(raw: str) -> str:
    """Return SHA-256 hex digest of *raw* token string."""
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_refresh_token(raw: str) -> str:
    """Public alias used by services."""
    return _hash_token(raw)


def generate_jti() -> str:
    """Generate a cryptographically secure random identifier."""
    return secrets.token_hex(32)
