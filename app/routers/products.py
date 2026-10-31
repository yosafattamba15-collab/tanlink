"""Product router — public browsing + farmer CRUD."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.dependencies import DbDep, FarmerDep
from app.schemas.product import (
    CategoryOut,
    ProductCreate,
    ProductFilter,
    ProductListOut,
    ProductOut,
    ProductUpdate,
)
from app.services import product_service

router = APIRouter(tags=["Products"])


# ── Categories (public) ───────────────────────────────────────────────────────

@router.get(
    "/categories",
    response_model=list[CategoryOut],
    summary="Daftar semua kategori produk",
)
def get_categories(db: DbDep) -> list[CategoryOut]:
    """Kembalikan semua kategori yang tersedia."""
    cats = product_service.list_categories(db)
    return [CategoryOut.model_validate(c) for c in cats]


# ── Public product listing ────────────────────────────────────────────────────

@router.get(
    "/products",
    response_model=ProductListOut,
    summary="Daftar produk (publik, dengan filter)",
)
def list_products(
    db: DbDep,
    search: str | None = Query(default=None, description="Cari berdasarkan nama"),
    category_slug: str | None = Query(default=None),
    province: str | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ProductListOut:
    """Tampilkan produk aktif dengan pencarian nama, filter kategori, lokasi, dan harga."""
    filters = ProductFilter(
        search=search,
        category_slug=category_slug,
        province=province,
        min_price=min_price,
        max_price=max_price,
        page=page,
        page_size=page_size,
    )
    result = product_service.list_products(db, filters)
    return ProductListOut(**result)


@router.get(
    "/products/{product_id}",
    response_model=ProductOut,
    summary="Detail produk",
)
def get_product(product_id: str, db: DbDep) -> ProductOut:
    """Kembalikan detail lengkap satu produk aktif."""
    data = product_service.get_product(db, product_id)
    return ProductOut(**data)


# ── Farmer profile — produk per petani (publik) ───────────────────────────────

@router.get(
    "/users/{farmer_id}/products",
    response_model=list[ProductOut],
    summary="Profil petani: daftar produknya",
)
def get_farmer_products(farmer_id: str, db: DbDep) -> list[ProductOut]:
    """Tampilkan semua produk aktif milik satu petani (untuk halaman profil)."""
    items = product_service.list_farmer_products(db, farmer_id)
    return [ProductOut(**item) for item in items]


# ── Farmer CRUD (requires auth + role=farmer) ─────────────────────────────────

@router.post(
    "/products",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah produk baru (petani)",
)
async def create_product(
    db: DbDep,
    farmer: FarmerDep,
    # Form fields — sent as multipart/form-data alongside the image file
    category_id: str = Form(...),
    name: str = Form(..., min_length=2, max_length=200),
    description: str | None = Form(default=None),
    price: float = Form(..., gt=0),
    unit: str = Form(..., min_length=1, max_length=30),
    stock: int = Form(default=0, ge=0),
    province: str | None = Form(default=None),
    city: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
) -> ProductOut:
    """Buat produk baru.  Kirim sebagai `multipart/form-data`.
    Foto opsional (jpg/png/webp, maks 3 MB).
    """
    payload = ProductCreate(
        category_id=category_id,
        name=name,
        description=description,
        price=Decimal(str(price)),
        unit=unit,
        stock=stock,
        province=province,
        city=city,
    )
    data = await product_service.create_product(db, farmer, payload, image)
    return ProductOut(**data)


@router.patch(
    "/products/{product_id}",
    response_model=ProductOut,
    summary="Update produk (petani pemilik)",
)
async def update_product(
    product_id: str,
    db: DbDep,
    farmer: FarmerDep,
    category_id: str | None = Form(default=None),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    price: float | None = Form(default=None),
    unit: str | None = Form(default=None),
    stock: int | None = Form(default=None),
    province: str | None = Form(default=None),
    city: str | None = Form(default=None),
    is_active: bool | None = Form(default=None),
    image: UploadFile | None = File(default=None),
) -> ProductOut:
    """Update satu atau lebih field produk.  Kirim sebagai `multipart/form-data`."""
    payload = ProductUpdate(
        category_id=category_id,
        name=name,
        description=description,
        price=Decimal(str(price)) if price is not None else None,
        unit=unit,
        stock=stock,
        province=province,
        city=city,
        is_active=is_active,
    )
    data = await product_service.update_product(db, farmer, product_id, payload, image)
    return ProductOut(**data)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus produk (petani pemilik) — soft delete",
)
def delete_product(product_id: str, db: DbDep, farmer: FarmerDep) -> None:
    """Nonaktifkan produk (soft-delete).  Produk tidak akan muncul di listing publik."""
    product_service.delete_product(db, farmer, product_id)
