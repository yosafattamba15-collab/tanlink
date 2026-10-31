"""pytest configuration and shared fixtures for Tanilink tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.category import Category
from app.core.dependencies import get_db

# Use an in-memory SQLite database for tests — no PostgreSQL required.
# SQLite is structurally compatible with our models for unit-test purposes.
TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


# Default categories (mirrors migration 0002)
_DEFAULT_CATEGORIES = [
    ("Sayur-mayur",  "sayur"),
    ("Buah-buahan",  "buah"),
    ("Perkebunan",   "perkebunan"),
    ("Padi & Beras", "padi-beras"),
    ("Rempah",       "rempah"),
    ("Peternakan",   "peternakan"),
    ("Perikanan",    "perikanan"),
    ("Lainnya",      "lainnya"),
]


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables + seed categories once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    # Seed categories
    with TestingSessionLocal() as session:
        for name, slug in _DEFAULT_CATEGORIES:
            session.add(Category(id=str(uuid.uuid4()), name=name, slug=slug))
        session.commit()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db():
    """Yield a clean DB session per test; rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    """TestClient with get_db overridden to use the test session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass  # rollback handled by the db fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FARMER_PAYLOAD = {
    "full_name": "Pak Tani",
    "email": "paktani@example.com",
    "password": "password123",
    "role": "farmer",
    "province": "Jawa Barat",
    "city": "Bandung",
}

BUYER_PAYLOAD = {
    "full_name": "Bu Beli",
    "email": "bubeli@example.com",
    "password": "password456",
    "role": "buyer",
}


def register_and_get_token(client: TestClient, payload: dict) -> str:
    """Register a user and return their access token."""
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return resp.json()["access_token"]
