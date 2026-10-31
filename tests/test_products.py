"""Unit tests for product endpoints."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.conftest import BUYER_PAYLOAD, FARMER_PAYLOAD, register_and_get_token


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def farmer_token(client: TestClient) -> str:
    return register_and_get_token(client, FARMER_PAYLOAD)


@pytest.fixture()
def buyer_token(client: TestClient) -> str:
    return register_and_get_token(client, BUYER_PAYLOAD)


@pytest.fixture()
def farmer_headers(farmer_token: str) -> dict:
    return {"Authorization": f"Bearer {farmer_token}"}


@pytest.fixture()
def buyer_headers(buyer_token: str) -> dict:
    return {"Authorization": f"Bearer {buyer_token}"}


@pytest.fixture()
def category_id(client: TestClient) -> str:
    """Return the first category slug's ID from the seeded categories."""
    resp = client.get("/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) > 0
    return cats[0]["id"]


def _make_product_form(category_id: str, **overrides) -> dict:
    base = {
        "category_id": category_id,
        "name":        "Bayam Segar",
        "description": "Bayam organik dari kebun sendiri",
        "price":       "5000",
        "unit":        "ikat",
        "stock":       "100",
        "province":    "Jawa Barat",
        "city":        "Bandung",
    }
    base.update(overrides)
    return base


def _fake_image(content_type: str = "image/jpeg") -> tuple:
    """Return a (filename, file-like, content_type) tuple for multipart upload."""
    return ("test.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 100), content_type)


# ── GET /categories ───────────────────────────────────────────────────────────

class TestCategories:
    def test_list_categories_returns_defaults(self, client: TestClient):
        resp = client.get("/categories")
        assert resp.status_code == 200
        data = resp.json()
        slugs = {c["slug"] for c in data}
        assert "sayur" in slugs
        assert "buah" in slugs

    def test_list_categories_has_required_fields(self, client: TestClient):
        resp = client.get("/categories")
        first = resp.json()[0]
        assert "id" in first
        assert "name" in first
        assert "slug" in first


# ── POST /products ────────────────────────────────────────────────────────────

class TestCreateProduct:
    def test_farmer_can_create_product(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=farmer_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Bayam Segar"
        assert data["unit"] == "ikat"
        assert data["farmer"]["province"] == "Jawa Barat"
        assert data["category"]["slug"] in ("sayur", "buah", "perkebunan",
                                             "padi-beras", "rempah",
                                             "peternakan", "perikanan", "lainnya")

    def test_buyer_cannot_create_product(
        self, client: TestClient, buyer_headers: dict, category_id: str
    ):
        resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=buyer_headers,
        )
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_product(
        self, client: TestClient, category_id: str
    ):
        resp = client.post("/products", data=_make_product_form(category_id))
        assert resp.status_code == 403  # HTTPBearer returns 403 when no credentials

    def test_invalid_category_returns_400(
        self, client: TestClient, farmer_headers: dict
    ):
        resp = client.post(
            "/products",
            data=_make_product_form("nonexistent-uuid"),
            headers=farmer_headers,
        )
        assert resp.status_code == 400

    def test_negative_price_returns_422(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        resp = client.post(
            "/products",
            data=_make_product_form(category_id, price="-100"),
            headers=farmer_headers,
        )
        assert resp.status_code == 422

    def test_image_wrong_type_returns_400(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            files={"image": ("test.gif", io.BytesIO(b"GIF89a"), "image/gif")},
            headers=farmer_headers,
        )
        assert resp.status_code == 400

    def test_image_too_large_returns_400(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        big = io.BytesIO(b"\xff\xd8\xff" + b"\x00" * (4 * 1024 * 1024))  # 4 MB
        resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            files={"image": ("big.jpg", big, "image/jpeg")},
            headers=farmer_headers,
        )
        assert resp.status_code == 400


# ── GET /products ─────────────────────────────────────────────────────────────

class TestListProducts:
    def _create(self, client, headers, category_id, **overrides):
        client.post(
            "/products",
            data=_make_product_form(category_id, **overrides),
            headers=headers,
        )

    def test_list_returns_active_products(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        self._create(client, farmer_headers, category_id)
        resp = client.get("/products")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] >= 1
        assert data["page"] == 1

    def test_search_by_name(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        self._create(client, farmer_headers, category_id, name="Tomat Merah")
        resp = client.get("/products?search=Tomat")
        assert resp.status_code == 200
        names = [i["name"] for i in resp.json()["items"]]
        assert any("Tomat" in n for n in names)

    def test_filter_by_province(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        self._create(client, farmer_headers, category_id, province="Sulawesi Selatan")
        resp = client.get("/products?province=Sulawesi")
        items = resp.json()["items"]
        assert all("Sulawesi" in (i["province"] or "") for i in items)

    def test_filter_by_price_range(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        self._create(client, farmer_headers, category_id, price="3000")
        resp = client.get("/products?min_price=1000&max_price=4000")
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert float(item["price"]) <= 4000

    def test_pagination(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        for i in range(5):
            self._create(client, farmer_headers, category_id, name=f"Produk {i}")
        resp = client.get("/products?page=1&page_size=2")
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["page_size"] == 2


# ── GET /products/{id} ────────────────────────────────────────────────────────

class TestGetProduct:
    def test_get_existing_product(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        create_resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=farmer_headers,
        )
        pid = create_resp.json()["id"]
        resp = client.get(f"/products/{pid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_get_nonexistent_returns_404(self, client: TestClient):
        resp = client.get("/products/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ── PATCH /products/{id} ──────────────────────────────────────────────────────

class TestUpdateProduct:
    def _create_and_get_id(self, client, headers, category_id) -> str:
        resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=headers,
        )
        return resp.json()["id"]

    def test_farmer_can_update_own_product(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        pid = self._create_and_get_id(client, farmer_headers, category_id)
        resp = client.patch(
            f"/products/{pid}",
            data={"name": "Bayam Super", "stock": "200"},
            headers=farmer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bayam Super"
        assert resp.json()["stock"] == 200

    def test_buyer_cannot_update_product(
        self, client: TestClient, farmer_headers: dict,
        buyer_headers: dict, category_id: str
    ):
        pid = self._create_and_get_id(client, farmer_headers, category_id)
        resp = client.patch(
            f"/products/{pid}",
            data={"stock": "50"},
            headers=buyer_headers,
        )
        assert resp.status_code == 403


# ── DELETE /products/{id} ─────────────────────────────────────────────────────

class TestDeleteProduct:
    def test_farmer_can_soft_delete(
        self, client: TestClient, farmer_headers: dict, category_id: str
    ):
        create_resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=farmer_headers,
        )
        pid = create_resp.json()["id"]
        del_resp = client.delete(f"/products/{pid}", headers=farmer_headers)
        assert del_resp.status_code == 204
        # Product should no longer appear in public list
        get_resp = client.get(f"/products/{pid}")
        assert get_resp.status_code == 404

    def test_buyer_cannot_delete(
        self, client: TestClient, farmer_headers: dict,
        buyer_headers: dict, category_id: str
    ):
        create_resp = client.post(
            "/products",
            data=_make_product_form(category_id),
            headers=farmer_headers,
        )
        pid = create_resp.json()["id"]
        resp = client.delete(f"/products/{pid}", headers=buyer_headers)
        assert resp.status_code == 403
