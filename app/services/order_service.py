"""Order business logic: checkout, status updates, listing."""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderStatusUpdate
from app.services import cart_service


# ── Serialisation ─────────────────────────────────────────────────────────────

def _serialize_order(order: Order) -> dict:
    items = []
    for oi in order.items:
        p = oi.product
        unit_price = Decimal(str(oi.unit_price))
        items.append({
            "id":                oi.id,
            "product_id":        p.id,
            "product_name":      p.name,
            "product_image_url": p.image_url,
            "unit":              p.unit,
            "unit_price":        unit_price,
            "quantity":          oi.quantity,
            "subtotal":          unit_price * oi.quantity,
        })
    return {
        "id":          order.id,
        "status":      order.status.value,
        "total_price": Decimal(str(order.total_price)),
        "note":        order.note,
        "created_at":  order.created_at.isoformat(),
        "updated_at":  order.updated_at.isoformat(),
        "buyer_id":    order.buyer_id,
        "items":       items,
    }


def _load_order(db: Session, order_id: str) -> Order:
    order = db.execute(
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.id == order_id)
    ).scalars().first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pesanan tidak ditemukan.")
    return order


# ── Checkout ──────────────────────────────────────────────────────────────────

def checkout(db: Session, buyer: User, payload: OrderCreate) -> dict:
    """Convert the buyer's current cart into a confirmed Order.

    Steps:
    1. Load cart + items
    2. Validate stock for each item
    3. Deduct stock
    4. Create Order + OrderItems (price snapshot)
    5. Clear cart
    """
    if buyer.role != UserRole.buyer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya pembeli yang dapat checkout.")

    cart = db.execute(
        select(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .where(Cart.user_id == buyer.id)
    ).scalars().first()

    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keranjang kosong. Tambah produk terlebih dahulu.",
        )

    total = Decimal("0")
    order_items_data = []

    for ci in cart.items:
        p = ci.product
        if not p.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Produk '{p.name}' sudah tidak tersedia.",
            )
        if ci.quantity > p.stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stok '{p.name}' tidak mencukupi (tersedia: {p.stock}).",
            )
        unit_price = Decimal(str(p.price))
        total += unit_price * ci.quantity
        order_items_data.append((p, ci.quantity, unit_price))

    # Deduct stock atomically
    for product, qty, _ in order_items_data:
        product.stock -= qty

    # Create order
    order = Order(
        buyer_id=buyer.id,
        status=OrderStatus.pending,
        total_price=total,
        note=payload.note,
    )
    db.add(order)
    db.flush()  # populate order.id

    for product, qty, unit_price in order_items_data:
        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            unit_price=unit_price,
        ))

    # Clear cart
    cart_service.clear_cart(db, cart)

    db.commit()
    return _serialize_order(_load_order(db, order.id))


# ── Status update ─────────────────────────────────────────────────────────────

# Allowed status transitions
_TRANSITIONS: dict[OrderStatus, set[str]] = {
    OrderStatus.pending:    {"processing", "cancelled"},
    OrderStatus.processing: {"completed",  "cancelled"},
    OrderStatus.completed:  set(),   # terminal
    OrderStatus.cancelled:  set(),   # terminal
}


def update_order_status(
    db: Session, actor: User, order_id: str, payload: OrderStatusUpdate
) -> dict:
    """Update order status.

    Rules:
    - The buyer can cancel their own pending order.
    - The farmer who owns any item in the order can move it forward/cancel.
    - Status transitions must follow the allowed graph.
    """
    order = _load_order(db, order_id)
    new_status = payload.status

    # Validate transition
    allowed = _TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tidak bisa mengubah status dari '{order.status.value}' ke '{new_status}'.",
        )

    # Authorisation
    if actor.role == UserRole.buyer:
        if order.buyer_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan pesanan Anda.")
        if new_status != "cancelled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Pembeli hanya bisa membatalkan pesanan.",
            )
    elif actor.role == UserRole.farmer:
        farmer_owns = any(oi.product.farmer_id == actor.id for oi in order.items)
        if not farmer_owns:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki produk dalam pesanan ini.",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    # Restore stock on cancellation
    if new_status == "cancelled":
        for oi in order.items:
            oi.product.stock += oi.quantity

    order.status = OrderStatus(new_status)
    db.commit()
    return _serialize_order(_load_order(db, order.id))


# ── Listing ───────────────────────────────────────────────────────────────────

def list_my_orders(db: Session, buyer: User) -> list[dict]:
    """Return all orders for the authenticated buyer, newest first."""
    orders = db.execute(
        select(Order)
        .options(joinedload(Order.items).joinedload(OrderItem.product))
        .where(Order.buyer_id == buyer.id)
        .order_by(Order.created_at.desc())
    ).scalars().all()
    return [_serialize_order(o) for o in orders]


def get_order_detail(db: Session, actor: User, order_id: str) -> dict:
    """Return order detail — buyer sees own orders; farmer sees orders with their products."""
    order = _load_order(db, order_id)

    if actor.role == UserRole.buyer:
        if order.buyer_id != actor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bukan pesanan Anda.")
    elif actor.role == UserRole.farmer:
        farmer_owns = any(oi.product.farmer_id == actor.id for oi in order.items)
        if not farmer_owns:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak.")

    return _serialize_order(order)
