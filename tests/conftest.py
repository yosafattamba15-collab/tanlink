"""pytest configuration and shared fixtures for Tanilink tests."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.models.category import Category
from app.core.dependencies import get_db

# Use a true in-memory SQLite DB with StaticPool so every connection shares
# the same in-memory DB within a test.  This guarantees a perfectly clean
# slate for each test (tables are dropped + recreated) with no on-disk file
# that could leak token_hash UNIQUE violations between tests.
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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


@pytest.fixture(scope="function", autouse=True)
def create_test_tables():
    """Create tables + seed categories for every test; drop after.

    StaticPool + in-memory DB means each test sees a completely fresh DB.
    """
    Base.metadata.create_all(bind=test_engine)
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
