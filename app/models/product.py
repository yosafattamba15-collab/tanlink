"""Product ORM model."""

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Product(Base, TimestampMixin):
    """A product listed by a farmer (petani)."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    farmer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)  # kg, ikat, buah, dll.
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Denormalised location for fast filtering (no join to users needed)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    farmer: Mapped["User"] = relationship("User", foreign_keys=[farmer_id])  # type: ignore[name-defined]
    category: Mapped["Category"] = relationship("Category", back_populates="products")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name}>"
