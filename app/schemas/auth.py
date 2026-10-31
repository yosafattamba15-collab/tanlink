"""Pydantic v2 schemas for authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    full_name: str = Field(..., min_length=2, max_length=100, examples=["Budi Santoso"])
    email: EmailStr
    phone: str | None = Field(default=None, pattern=r"^(\+62|0)[0-9]{8,13}$")
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(..., pattern="^(farmer|buyer)$")
    province: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_not_whitespace(cls, v: str) -> str:
        if v.strip() != v:
            raise ValueError("Password tidak boleh diawali/diakhiri spasi.")
        return v


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Payload for POST /auth/logout."""

    refresh_token: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    """Public user representation embedded in token responses."""

    model_config = {"from_attributes": True}

    id: str
    full_name: str
    email: str
    role: str
    province: str | None
    city: str | None
    avatar_url: str | None


class TokenResponse(BaseModel):
    """Returned after successful login or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageResponse(BaseModel):
    """Generic success message response."""

    success: bool = True
    message: str
