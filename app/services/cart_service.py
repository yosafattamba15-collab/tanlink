"""Cart business logic: add item, view, update quantity, remove, clear."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import CartItemAdd, CartItemUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_cart(db: Session, user: User) -> Cart:
    """Return existing cart or create a new one for the user."""
    cart = db.execute(
        select(Cart).where(Cart.user_id == user.id)
    ).scalars().first()
    if not cart:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.flush()
    return cart


def _get_active_product(db: Session, product_id: str) -> Product:
    product = db.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produk tidak ditemukan atau sudah tidak aktif.",
        )
    return product


def _serialize_cart(cart: Cart) -> dict:
    items = []
    total = Decimal("0")
    for ci in cart.items:
        p = ci.product
        unit_price = Decimal(str(p.price))
        subtotal   = unit_price * ci.quantity
        total     += subtotal
        items.append({
            "id":                ci.id,
            "product_id":        p.id,
            "product_name":      p.name,
            "product_image_url": p.image_url,
            "unit":              p.unit,
            "unit_price":        unit_price,
            "quantity":          ci.quantity,
            "subtotal":          subtotal,
        })
    return {"id": cart.id, "items": items, "total": total}


def _load_cart_with_items(db: Session, user: User) -> Cart:
    cart = db.execute(
        select(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .where(Cart.user_id == user.id)
    ).scalars().first()
    return cart


# ── Public API ────────────────────────────────────────────────────────────────

def get_cart(db: Session, user: User) -> dict:
    """Return current cart (empty cart if none exists)."""
    cart = _load_cart_with_items(db, user)
    if not cart:
        return {"id": None, "items": [], "total": Decimal("0")}
    return _serialize_cart(cart)


def add_item(db: Session, user: User, payload: CartItemAdd) -> dict:
    """Add product to cart or increment quantity if already present.

    Validates product is active and quantity does not exceed stock.
    """
    product = _get_active_product(db, payload.product_id)

    if payload.quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stok tidak cukup. Tersedia: {product.stock}.",
        )

    cart = _get_or_create_cart(db, user)

    # Check if item already in cart
    existing = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == payload.product_id,
        )
    ).scalars().first()

    if existing:
        new_qty = existing.quantity + payload.quantity
        if new_qty > product.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total kuantitas melebihi stok. Tersedia: {product.stock}.",
            )
        existing.quantity = new_qty
    else:
        db.add(CartItem(cart_id=cart.id, product_id=payload.product_id, quantity=payload.quantity))

    db.commit()
    return get_cart(db, user)


def update_item(db: Session, user: User, item_id: str, payload: CartItemUpdate) -> dict:
    """Set exact quantity for an existing cart item."""
    cart = _get_or_create_cart(db, user)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalars().first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item tidak ditemukan di keranjang.")

    product = _get_active_product(db, item.product_id)
    if payload.quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stok tidak cukup. Tersedia: {product.stock}.",
        )

    item.quantity = payload.quantity
    db.commit()
    return get_cart(db, user)


def remove_item(db: Session, user: User, item_id: str) -> dict:
    """Remove a single item from the cart."""
    cart = _get_or_create_cart(db, user)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalars().first()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item tidak ditemukan di keranjang.")

    db.delete(item)
    db.commit()
    return get_cart(db, user)


def clear_cart(db: Session, cart: Cart) -> None:
    """Delete all items in a cart (called internally after checkout)."""
    for item in cart.items:
        db.delete(item)
    db.flush()
