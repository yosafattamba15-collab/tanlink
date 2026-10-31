"""Pydantic v2 schemas for cart and order endpoints."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


# ── Cart ──────────────────────────────────────────────────────────────────────

class CartItemAdd(BaseModel):
    """Add or update a product in the cart."""

    product_id: str
    quantity: int = Field(..., ge=1, le=9999)


class CartItemUpdate(BaseModel):
    """Change quantity of an existing cart item."""

    quantity: int = Field(..., ge=1, le=9999)


class CartItemOut(BaseModel):
    """One line in the cart response."""

    id: str
    product_id: str
    product_name: str
    product_image_url: str | None
    unit: str
    unit_price: Decimal        # current product price
    quantity: int
    subtotal: Decimal


class CartOut(BaseModel):
    """Full cart response."""

    id: str | None   # None when cart has never been created (empty state)
    items: list[CartItemOut]
    total: Decimal


# ── Order ─────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """Payload for POST /orders — checkout from current cart."""

    note: str | None = Field(default=None, max_length=500)


class OrderStatusUpdate(BaseModel):
    """Payload for PATCH /orders/{id}/status — petani updates order status."""

    status: str = Field(..., pattern="^(processing|completed|cancelled)$")


class OrderItemOut(BaseModel):
    """One product line in an order (price snapshot)."""

    id: str
    product_id: str
    product_name: str
    product_image_url: str | None
    unit: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderOut(BaseModel):
    """Full order detail response."""

    id: str
    status: str
    total_price: Decimal
    note: str | None
    created_at: str
    updated_at: str
    buyer_id: str
    items: list[OrderItemOut]
