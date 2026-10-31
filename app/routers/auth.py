"""Auth router — register, login, token refresh, logout."""

from fastapi import APIRouter, status

from app.core.dependencies import DbDep
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrasi user baru",
)
def register(payload: RegisterRequest, db: DbDep) -> TokenResponse:
    """Daftarkan user baru (petani atau pembeli).

    Mengembalikan access + refresh token agar user langsung login setelah daftar.
    """
    access_token, raw_refresh, user = auth_service.register_user(db, payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login dengan email dan password",
)
def login(payload: LoginRequest, db: DbDep) -> TokenResponse:
    """Autentikasi user dan kembalikan token pair."""
    access_token, raw_refresh, user = auth_service.login_user(db, payload)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Tukar refresh token dengan access token baru",
)
def refresh(payload: RefreshRequest, db: DbDep) -> TokenResponse:
    """Token rotation: refresh token lama direvoke, pasangan token baru diterbitkan."""
    access_token, raw_refresh, user = auth_service.refresh_access_token(
        db, payload.refresh_token
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout — revoke refresh token",
)
def logout(payload: LogoutRequest, db: DbDep) -> MessageResponse:
    """Revoke refresh token yang diberikan. Idempotent."""
    auth_service.logout_user(db, payload.refresh_token)
    return MessageResponse(message="Logout berhasil.")
