"""Cart router — buyer manages their shopping cart."""

from fastapi import APIRouter, status

from app.core.dependencies import BuyerDep, CurrentUser, DbDep
from app.schemas.order import CartItemAdd, CartItemUpdate, CartOut
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=CartOut,
    summary="Lihat keranjang belanja",
)
def get_cart(db: DbDep, current_user: CurrentUser) -> CartOut:
    """Kembalikan isi keranjang aktif milik user yang sedang login."""
    data = cart_service.get_cart(db, current_user)
    return CartOut(**data)


@router.post(
    "/items",
    response_model=CartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah produk ke keranjang",
)
def add_item(payload: CartItemAdd, db: DbDep, buyer: BuyerDep) -> CartOut:
    """Tambah produk ke keranjang.  Jika sudah ada, kuantitas diakumulasi."""
    data = cart_service.add_item(db, buyer, payload)
    return CartOut(**data)


@router.patch(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Ubah kuantitas item di keranjang",
)
def update_item(item_id: str, payload: CartItemUpdate, db: DbDep, buyer: BuyerDep) -> CartOut:
    """Set kuantitas tepat untuk satu item keranjang."""
    data = cart_service.update_item(db, buyer, item_id, payload)
    return CartOut(**data)


@router.delete(
    "/items/{item_id}",
    response_model=CartOut,
    summary="Hapus item dari keranjang",
)
def remove_item(item_id: str, db: DbDep, buyer: BuyerDep) -> CartOut:
    """Hapus satu item dari keranjang, kembalikan state keranjang terbaru."""
    data = cart_service.remove_item(db, buyer, item_id)
    return CartOut(**data)
