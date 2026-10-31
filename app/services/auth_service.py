"""Auth business logic: register, login, refresh token, logout."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest

settings = get_settings()


def register_user(db: Session, payload: RegisterRequest) -> tuple[str, str, User]:
    """Register a new user and return (access_token, refresh_token, user).

    Raises HTTP 409 if email is already taken.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email sudah terdaftar.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=UserRole(payload.role),
        province=payload.province,
        city=payload.city,
    )
    db.add(user)
    db.flush()  # populate user.id before creating token

    access_token, raw_refresh, token_record = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return access_token, raw_refresh, user


def login_user(db: Session, payload: LoginRequest) -> tuple[str, str, User]:
    """Verify credentials and return (access_token, refresh_token, user).

    Raises HTTP 401 on bad credentials.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun Anda dinonaktifkan.",
        )

    access_token, raw_refresh, _ = _issue_tokens(db, user)
    db.commit()
    return access_token, raw_refresh, user


def refresh_access_token(db: Session, raw_refresh_token: str) -> tuple[str, str, User]:
    """Validate refresh token, rotate it, return new (access_token, refresh_token, user).

    Token rotation: old token is revoked, new one issued.
    Raises HTTP 401 on any invalid/revoked/expired token.
    """
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token tidak valid atau sudah kedaluwarsa.",
    )

    # 1. Decode JWT to get user_id
    try:
        payload = decode_token(raw_refresh_token)
        if payload.get("type") != "refresh":
            raise invalid_exc
        user_id: str = payload["sub"]
    except JWTError:
        raise invalid_exc

    # 2. Look up hash in DB
    token_hash = hash_refresh_token(raw_refresh_token)
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if not record or record.revoked:
        raise invalid_exc
    if record.expires_at < datetime.now(timezone.utc):
        raise invalid_exc

    # 3. Revoke old token (rotation)
    record.revoked = True
    db.flush()

    # 4. Issue new token pair
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise invalid_exc

    access_token, raw_refresh, _ = _issue_tokens(db, user)
    db.commit()
    return access_token, raw_refresh, user


def logout_user(db: Session, raw_refresh_token: str) -> None:
    """Revoke the given refresh token.

    Silently succeeds even if token is not found (idempotent).
    """
    try:
        decode_token(raw_refresh_token)  # basic format check
    except JWTError:
        return  # already invalid — nothing to revoke

    token_hash = hash_refresh_token(raw_refresh_token)
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if record and not record.revoked:
        record.revoked = True
        db.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _issue_tokens(
    db: Session, user: User
) -> tuple[str, str, RefreshToken]:
    """Create access + refresh token pair; persist refresh token hash to DB."""
    access_token = create_access_token(user.id)
    raw_refresh, token_hash = create_refresh_token(user.id)

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token_record)
    return access_token, raw_refresh, token_record
