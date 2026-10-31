"""FastAPI dependency functions shared across routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

def get_db():
    """Yield a SQLAlchemy session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: DbDep,
) -> User:
    """Validate Bearer access token and return the authenticated User.

    Raises HTTP 401 on any invalid / expired token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sudah kedaluwarsa.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_farmer(current_user: CurrentUser) -> User:
    """Guard: current user must have role='farmer'."""
    if current_user.role != "farmer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya petani yang dapat melakukan aksi ini.",
        )
    return current_user


def require_buyer(current_user: CurrentUser) -> User:
    """Guard: current user must have role='buyer'."""
    if current_user.role != "buyer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya pembeli yang dapat melakukan aksi ini.",
        )
    return current_user


FarmerDep = Annotated[User, Depends(require_farmer)]
BuyerDep = Annotated[User, Depends(require_buyer)]
