"""Unit tests for the auth module (/auth/register, /auth/login, /auth/refresh, /auth/logout)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import BUYER_PAYLOAD, FARMER_PAYLOAD, register_and_get_token


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ──────────────────────────────────────────────────────────────────────────────

class TestRegister:
    def test_register_farmer_success(self, client: TestClient):
        resp = client.post("/auth/register", json=FARMER_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["token_type"] == "bearer"
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["user"]["role"] == "farmer"
        assert data["user"]["email"] == FARMER_PAYLOAD["email"]

    def test_register_buyer_success(self, client: TestClient):
        resp = client.post("/auth/register", json=BUYER_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "buyer"

    def test_register_duplicate_email(self, client: TestClient):
        client.post("/auth/register", json=FARMER_PAYLOAD)
        resp = client.post("/auth/register", json=FARMER_PAYLOAD)
        assert resp.status_code == 409
        assert "Email sudah terdaftar" in resp.json()["detail"]

    def test_register_invalid_role(self, client: TestClient):
        payload = {**FARMER_PAYLOAD, "role": "admin", "email": "other@example.com"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422  # Pydantic validation error

    def test_register_short_password(self, client: TestClient):
        payload = {**FARMER_PAYLOAD, "password": "short", "email": "x@example.com"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        payload = {**FARMER_PAYLOAD, "email": "not-an-email"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_phone(self, client: TestClient):
        payload = {**FARMER_PAYLOAD, "phone": "12345", "email": "phone@example.com"}
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client: TestClient):
        client.post("/auth/register", json=FARMER_PAYLOAD)
        resp = client.post(
            "/auth/login",
            json={"email": FARMER_PAYLOAD["email"], "password": FARMER_PAYLOAD["password"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["user"]["email"] == FARMER_PAYLOAD["email"]

    def test_login_wrong_password(self, client: TestClient):
        client.post("/auth/register", json=FARMER_PAYLOAD)
        resp = client.post(
            "/auth/login",
            json={"email": FARMER_PAYLOAD["email"], "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client: TestClient):
        resp = client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "password123"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: TestClient):
        resp = client.post("/auth/login", json={"email": "x@example.com"})
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/refresh
# ──────────────────────────────────────────────────────────────────────────────

class TestRefreshToken:
    def _get_tokens(self, client: TestClient) -> tuple[str, str]:
        resp = client.post("/auth/register", json=FARMER_PAYLOAD)
        data = resp.json()
        return data["access_token"], data["refresh_token"]

    def test_refresh_returns_new_token_pair(self, client: TestClient):
        _, refresh = self._get_tokens(client)
        resp = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        # New refresh token must differ (rotation)
        assert data["refresh_token"] != refresh

    def test_refresh_token_rotation_revokes_old(self, client: TestClient):
        """After rotation, re-using the old refresh token must fail."""
        _, old_refresh = self._get_tokens(client)
        client.post("/auth/refresh", json={"refresh_token": old_refresh})
        resp2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert resp2.status_code == 401

    def test_refresh_invalid_token(self, client: TestClient):
        resp = client.post("/auth/refresh", json={"refresh_token": "not.a.valid.token"})
        assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/logout
# ──────────────────────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_success(self, client: TestClient):
        resp_reg = client.post("/auth/register", json=FARMER_PAYLOAD)
        refresh = resp_reg.json()["refresh_token"]
        resp = client.post("/auth/logout", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_logout_then_refresh_fails(self, client: TestClient):
        """Refresh after logout must be rejected."""
        resp_reg = client.post("/auth/register", json=BUYER_PAYLOAD)
        refresh = resp_reg.json()["refresh_token"]
        client.post("/auth/logout", json={"refresh_token": refresh})
        resp = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 401

    def test_logout_idempotent(self, client: TestClient):
        """Logging out twice with the same token should not raise an error."""
        resp_reg = client.post("/auth/register", json=FARMER_PAYLOAD)
        refresh = resp_reg.json()["refresh_token"]
        client.post("/auth/logout", json={"refresh_token": refresh})
        resp2 = client.post("/auth/logout", json={"refresh_token": refresh})
        assert resp2.status_code == 200
