"""Unit tests for cart and order endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import BUYER_PAYLOAD, FARMER_PAYLOAD, register_and_get_token

# ── Helpers ───────────────────────────────────────────────────────────────────

FARMER2_PAYLOAD = {
    "full_name": "Pak Tani Dua",
    "email": "paktani2@example.com",
    "password": "password123",
    "role": "farmer",
    "province": "Jawa Tengah",
    "city": "Semarang",
}


@pytest.fixture()
def farmer_token(client: TestClient) -> str:
    return register_and_get_token(client, FARMER_PAYLOAD)


@pytest.fixture()
def farmer_headers(farmer_token: str) -> dict:
    return {"Authorization": f"Bearer {farmer_token}"}


@pytest.fixture()
def buyer_token(client: TestClient) -> str:
    return register_and_get_token(client, BUYER_PAYLOAD)


@pytest.fixture()
def buyer_headers(buyer_token: str) -> dict:
    return {"Authorization": f"Bearer {buyer_token}"}


@pytest.fixture()
def category_id(client: TestClient) -> str:
    resp = client.get("/categories")
    return resp.json()[0]["id"]


@pytest.fixture()
def product_id(client: TestClient, farmer_headers: dict, category_id: str) -> str:
    """Create a product and return its ID."""
    resp = client.post(
        "/products",
        data={
            "category_id": category_id,
            "name": "Kangkung Segar",
            "price": "3000",
            "unit": "ikat",
            "stock": "50",
        },
        headers=farmer_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ── GET /cart ─────────────────────────────────────────────────────────────────

class TestGetCart:
    def test_empty_cart_returns_zero_total(self, client: TestClient, buyer_headers: dict):
        resp = client.get("/cart", headers=buyer_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert float(data["total"]) == 0.0

    def test_unauthenticated_cannot_view_cart(self, client: TestClient):
        resp = client.get("/cart")
        assert resp.status_code == 403


# ── POST /cart/items ──────────────────────────────────────────────────────────

class TestAddCartItem:
    def test_buyer_adds_item(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        resp = client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": 2},
            headers=buyer_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert float(data["total"]) == pytest.approx(6000.0)

    def test_farmer_cannot_add_to_cart(
        self, client: TestClient, farmer_headers: dict, product_id: str
    ):
        resp = client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": 1},
            headers=farmer_headers,
        )
        assert resp.status_code == 403

    def test_add_same_product_accumulates_quantity(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        client.post("/cart/items", json={"product_id": product_id, "quantity": 3}, headers=buyer_headers)
        resp = client.post("/cart/items", json={"product_id": product_id, "quantity": 2}, headers=buyer_headers)
        assert resp.status_code == 201
        assert resp.json()["items"][0]["quantity"] == 5

    def test_exceed_stock_returns_400(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        resp = client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": 999},
            headers=buyer_headers,
        )
        assert resp.status_code == 400

    def test_nonexistent_product_returns_404(
        self, client: TestClient, buyer_headers: dict
    ):
        resp = client.post(
            "/cart/items",
            json={"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1},
            headers=buyer_headers,
        )
        assert resp.status_code == 404


# ── PATCH /cart/items/{item_id} ───────────────────────────────────────────────

class TestUpdateCartItem:
    def test_update_quantity(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        add = client.post(
            "/cart/items", json={"product_id": product_id, "quantity": 1}, headers=buyer_headers
        )
        item_id = add.json()["items"][0]["id"]
        resp = client.patch(
            f"/cart/items/{item_id}",
            json={"quantity": 10},
            headers=buyer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["items"][0]["quantity"] == 10


# ── DELETE /cart/items/{item_id} ──────────────────────────────────────────────

class TestRemoveCartItem:
    def test_remove_item(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        add = client.post(
            "/cart/items", json={"product_id": product_id, "quantity": 1}, headers=buyer_headers
        )
        item_id = add.json()["items"][0]["id"]
        resp = client.delete(f"/cart/items/{item_id}", headers=buyer_headers)
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_remove_nonexistent_item_returns_404(
        self, client: TestClient, buyer_headers: dict
    ):
        resp = client.delete("/cart/items/nonexistent-id", headers=buyer_headers)
        assert resp.status_code == 404


# ── POST /orders (checkout) ───────────────────────────────────────────────────

class TestCheckout:
    def _fill_cart(self, client, buyer_headers, product_id):
        client.post(
            "/cart/items",
            json={"product_id": product_id, "quantity": 2},
            headers=buyer_headers,
        )

    def test_checkout_creates_order(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        self._fill_cart(client, buyer_headers, product_id)
        resp = client.post("/orders", json={"note": "Kirim pagi"}, headers=buyer_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert float(data["total_price"]) == pytest.approx(6000.0)
        assert len(data["items"]) == 1
        assert data["note"] == "Kirim pagi"

    def test_checkout_clears_cart(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        self._fill_cart(client, buyer_headers, product_id)
        client.post("/orders", json={}, headers=buyer_headers)
        cart_resp = client.get("/cart", headers=buyer_headers)
        assert cart_resp.json()["items"] == []

    def test_checkout_deducts_stock(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        self._fill_cart(client, buyer_headers, product_id)
        client.post("/orders", json={}, headers=buyer_headers)
        product_resp = client.get(f"/products/{product_id}")
        assert product_resp.json()["stock"] == 48  # 50 - 2

    def test_checkout_empty_cart_returns_400(
        self, client: TestClient, buyer_headers: dict
    ):
        resp = client.post("/orders", json={}, headers=buyer_headers)
        assert resp.status_code == 400

    def test_farmer_cannot_checkout(
        self, client: TestClient, farmer_headers: dict
    ):
        resp = client.post("/orders", json={}, headers=farmer_headers)
        assert resp.status_code == 403


# ── GET /orders ───────────────────────────────────────────────────────────────

class TestListOrders:
    def test_buyer_sees_own_orders(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        client.post("/cart/items", json={"product_id": product_id, "quantity": 1}, headers=buyer_headers)
        client.post("/orders", json={}, headers=buyer_headers)
        resp = client.get("/orders", headers=buyer_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ── PATCH /orders/{id}/status ─────────────────────────────────────────────────

class TestOrderStatus:
    def _create_order(self, client, buyer_headers, product_id) -> str:
        client.post("/cart/items", json={"product_id": product_id, "quantity": 1}, headers=buyer_headers)
        resp = client.post("/orders", json={}, headers=buyer_headers)
        return resp.json()["id"]

    def test_farmer_moves_to_processing(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        order_id = self._create_order(client, buyer_headers, product_id)
        resp = client.patch(
            f"/orders/{order_id}/status",
            json={"status": "processing"},
            headers=farmer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processing"

    def test_farmer_moves_to_completed(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        order_id = self._create_order(client, buyer_headers, product_id)
        client.patch(f"/orders/{order_id}/status", json={"status": "processing"}, headers=farmer_headers)
        resp = client.patch(
            f"/orders/{order_id}/status",
            json={"status": "completed"},
            headers=farmer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_buyer_can_cancel_pending_order(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        order_id = self._create_order(client, buyer_headers, product_id)
        resp = client.patch(
            f"/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=buyer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_cancellation_restores_stock(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        initial_stock = client.get(f"/products/{product_id}").json()["stock"]
        order_id = self._create_order(client, buyer_headers, product_id)
        client.patch(
            f"/orders/{order_id}/status",
            json={"status": "cancelled"},
            headers=buyer_headers,
        )
        restored_stock = client.get(f"/products/{product_id}").json()["stock"]
        assert restored_stock == initial_stock

    def test_invalid_transition_returns_400(
        self, client: TestClient, buyer_headers: dict,
        farmer_headers: dict, product_id: str
    ):
        order_id = self._create_order(client, buyer_headers, product_id)
        # Cannot jump from pending → completed
        resp = client.patch(
            f"/orders/{order_id}/status",
            json={"status": "completed"},
            headers=farmer_headers,
        )
        assert resp.status_code == 400

    def test_buyer_cannot_set_processing(
        self, client: TestClient, buyer_headers: dict, product_id: str
    ):
        order_id = self._create_order(client, buyer_headers, product_id)
        resp = client.patch(
            f"/orders/{order_id}/status",
            json={"status": "processing"},
            headers=buyer_headers,
        )
        assert resp.status_code == 403
