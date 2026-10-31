"""Product business logic: CRUD, search/filter, image management."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductFilter, ProductUpdate
from app.services.storage_service import storage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize_product(p: Product) -> dict:
    """Convert a Product ORM object to a dict suitable for ProductOut/ProductListItem."""
    return {
        "id":          p.id,
        "name":        p.name,
        "description": p.description,
        "price":       p.price,
        "unit":        p.unit,
        "stock":       p.stock,
        "image_url":   p.image_url,
        "province":    p.province,
        "city":        p.city,
        "is_active":   p.is_active,
        "created_at":  p.created_at.isoformat(),
        "updated_at":  p.updated_at.isoformat(),
        "category": {
            "id":   p.category.id,
            "name": p.category.name,
            "slug": p.category.slug,
        },
        "farmer": {
            "id":        p.farmer.id,
            "full_name": p.farmer.full_name,
            "province":  p.farmer.province,
            "city":      p.farmer.city,
        },
    }


def _get_product_or_404(db: Session, product_id: str) -> Product:
    product = (
        db.execute(
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.farmer))
            .where(Product.id == product_id)
        )
        .scalars()
        .first()
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produk tidak ditemukan.")
    return product


def _require_category(db: Session, category_id: str) -> Category:
    cat = db.get(Category, category_id)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kategori tidak ditemukan.",
        )
    return cat


# ── Categories ────────────────────────────────────────────────────────────────

def list_categories(db: Session) -> list[Category]:
    """Return all categories ordered by name."""
    return list(db.execute(select(Category).order_by(Category.name)).scalars().all())


# ── Create ────────────────────────────────────────────────────────────────────

async def create_product(
    db: Session,
    farmer: User,
    payload: ProductCreate,
    image: UploadFile | None,
) -> dict:
    """Create a new product, optionally uploading an image.

    Only users with role='farmer' may call this (enforced at router level).
    """
    _require_category(db, payload.category_id)

    image_url: str | None = None
    if image and image.filename:
        image_url = await storage.save(image)

    product = Product(
        farmer_id=farmer.id,
        category_id=payload.category_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        unit=payload.unit,
        stock=payload.stock,
        image_url=image_url,
        province=payload.province or farmer.province,
        city=payload.city or farmer.city,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # Reload with relationships
    return _serialize_product(_get_product_or_404(db, product.id))


# ── Read (public) ─────────────────────────────────────────────────────────────

def get_product(db: Session, product_id: str) -> dict:
    """Return a single active product by ID."""
    product = _get_product_or_404(db, product_id)
    if not product.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produk tidak ditemukan.")
    return _serialize_product(product)


def list_products(db: Session, filters: ProductFilter) -> dict:
    """Return a paginated, filtered list of active products."""
    stmt = (
        select(Product)
        .options(joinedload(Product.category), joinedload(Product.farmer))
        .where(Product.is_active == True)  # noqa: E712
    )

    # ── Filters ──────────────────────────────────────────────────────────────
    if filters.search:
        stmt = stmt.where(Product.name.ilike(f"%{filters.search}%"))

    if filters.category_slug:
        stmt = stmt.join(Category).where(Category.slug == filters.category_slug)

    if filters.province:
        stmt = stmt.where(Product.province.ilike(f"%{filters.province}%"))

    if filters.min_price is not None:
        stmt = stmt.where(Product.price >= filters.min_price)

    if filters.max_price is not None:
        stmt = stmt.where(Product.price <= filters.max_price)

    # ── Count total before pagination ─────────────────────────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    # ── Pagination ────────────────────────────────────────────────────────────
    offset = (filters.page - 1) * filters.page_size
    stmt = stmt.order_by(Product.created_at.desc()).offset(offset).limit(filters.page_size)

    products = db.execute(stmt).scalars().all()
    total_pages = max(1, -(-total // filters.page_size))  # ceiling division

    return {
        "items":       [_serialize_product(p) for p in products],
        "total":       total,
        "page":        filters.page,
        "page_size":   filters.page_size,
        "total_pages": total_pages,
    }


def list_farmer_products(db: Session, farmer_id: str, include_inactive: bool = False) -> list[dict]:
    """Return all products belonging to a farmer (for farmer profile page)."""
    stmt = (
        select(Product)
        .options(joinedload(Product.category), joinedload(Product.farmer))
        .where(Product.farmer_id == farmer_id)
    )
    if not include_inactive:
        stmt = stmt.where(Product.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Product.created_at.desc())
    return [_serialize_product(p) for p in db.execute(stmt).scalars().all()]


# ── Update ────────────────────────────────────────────────────────────────────

async def update_product(
    db: Session,
    farmer: User,
    product_id: str,
    payload: ProductUpdate,
    image: UploadFile | None,
) -> dict:
    """Update product fields and/or replace image.

    Only the owning farmer may update their product.
    """
    product = _get_product_or_404(db, product_id)

    if product.farmer_id != farmer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan produk Anda.")

    if payload.category_id:
        _require_category(db, payload.category_id)

    # Apply field updates (only non-None values)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(product, field, value)

    # Replace image if a new one was uploaded
    if image and image.filename:
        old_url = product.image_url
        product.image_url = await storage.save(image)
        if old_url:
            storage.delete(old_url)

    db.commit()
    return _serialize_product(_get_product_or_404(db, product.id))


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_product(db: Session, farmer: User, product_id: str) -> None:
    """Soft-delete a product (set is_active=False).

    Only the owning farmer may delete their product.
    Hard-delete is intentionally avoided: existing order_items may reference this product.
    """
    product = _get_product_or_404(db, product_id)

    if product.farmer_id != farmer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan produk Anda.")

    product.is_active = False
    db.commit()
