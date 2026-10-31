"""Pydantic v2 schemas for categories and products."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_price(v: Decimal | None) -> Decimal | None:
    """Shared price validator: must be > 0 and max 2 decimal places."""
    if v is None:
        return v
    if v <= 0:
        raise ValueError("Harga harus lebih dari 0.")
    if v.as_tuple().exponent < -2:
        raise ValueError("Harga maksimal 2 angka desimal.")
    return v


# ── Category ──────────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    """Public category representation."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    slug: str


# ── Product request schemas ───────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """Payload for POST /products (form fields, image uploaded separately)."""

    category_id: str = Field(..., description="UUID of the category")
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(..., gt=0)
    unit: str = Field(..., min_length=1, max_length=30, examples=["kg", "ikat", "buah"])
    stock: int = Field(default=0, ge=0)
    province: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_whitespace_only(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nama produk tidak boleh hanya spasi.")
        return v.strip()

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        result = _validate_price(v)
        assert result is not None
        return result


class ProductUpdate(BaseModel):
    """Payload for PATCH /products/{id} — all fields optional."""

    category_id: str | None = None
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    stock: int | None = Field(default=None, ge=0)
    province: str | None = None
    city: str | None = None
    is_active: bool | None = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        return _validate_price(v)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ProductUpdate":
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("Minimal satu field harus diisi untuk update.")
        return self


# ── Product response schemas ──────────────────────────────────────────────────

class FarmerBrief(BaseModel):
    """Minimal farmer info embedded in product responses."""

    model_config = {"from_attributes": True}

    id: str
    full_name: str
    province: str | None
    city: str | None


class ProductOut(BaseModel):
    """Full product detail response."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    description: str | None
    price: Decimal
    unit: str
    stock: int
    image_url: str | None
    province: str | None
    city: str | None
    is_active: bool
    created_at: str  # ISO string — serialised in service
    updated_at: str

    category: CategoryOut
    farmer: FarmerBrief


class ProductListItem(BaseModel):
    """Compact product representation used in list endpoints."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    price: Decimal
    unit: str
    stock: int
    image_url: str | None
    province: str | None
    city: str | None
    is_active: bool
    category: CategoryOut
    farmer: FarmerBrief


class ProductListOut(BaseModel):
    """Paginated product list response."""

    items: list[ProductListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Filter / query params ─────────────────────────────────────────────────────

class ProductFilter(BaseModel):
    """Query-string parameters for GET /products."""

    search: str | None = None          # partial name match
    category_slug: str | None = None
    province: str | None = None
    min_price: Decimal | None = Field(default=None)
    max_price: Decimal | None = Field(default=None)

    @field_validator("min_price", "max_price")
    @classmethod
    def price_filter_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Filter harga tidak boleh negatif.")
        return v

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def max_gte_min(self) -> "ProductFilter":
        if self.min_price is not None and self.max_price is not None:
            if self.max_price < self.min_price:
                raise ValueError("max_price harus lebih besar dari min_price.")
        return self
