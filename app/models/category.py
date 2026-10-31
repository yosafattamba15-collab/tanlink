"""Category ORM model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class Category(Base):
    """Product category (sayur, buah, perkebunan, dll.)."""

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    products: Mapped[list["Product"]] = relationship(  # type: ignore[name-defined]
        "Product", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category slug={self.slug}>"
