"""Order router — checkout, status management, order history."""

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbDep
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout: buat pesanan dari keranjang",
)
def checkout(payload: OrderCreate, db: DbDep, current_user: CurrentUser) -> OrderOut:
    """Konversi keranjang aktif menjadi pesanan.
    Stok dikurangi secara atomik; keranjang dikosongkan setelah berhasil.
    """
    data = order_service.checkout(db, current_user, payload)
    return OrderOut(**data)


@router.get(
    "",
    response_model=list[OrderOut],
    summary="Riwayat pesanan saya (pembeli)",
)
def list_orders(db: DbDep, current_user: CurrentUser) -> list[OrderOut]:
    """Kembalikan semua pesanan milik pembeli yang sedang login, terbaru di atas."""
    items = order_service.list_my_orders(db, current_user)
    return [OrderOut(**o) for o in items]


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Detail satu pesanan",
)
def get_order(order_id: str, db: DbDep, current_user: CurrentUser) -> OrderOut:
    """Pembeli melihat pesanannya sendiri; petani melihat pesanan yang mengandung produknya."""
    data = order_service.get_order_detail(db, current_user, order_id)
    return OrderOut(**data)


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Update status pesanan",
)
def update_status(
    order_id: str,
    payload: OrderStatusUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> OrderOut:
    """Petani: pending→processing, processing→completed/cancelled.
    Pembeli: pending→cancelled saja.
    """
    data = order_service.update_order_status(db, current_user, order_id, payload)
    return OrderOut(**data)
