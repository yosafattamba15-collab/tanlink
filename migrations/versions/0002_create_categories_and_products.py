"""create categories and products tables, seed default categories

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None

# Default categories seeded on first migration
DEFAULT_CATEGORIES = [
    ("Sayur-mayur",  "sayur"),
    ("Buah-buahan",  "buah"),
    ("Perkebunan",   "perkebunan"),
    ("Padi & Beras", "padi-beras"),
    ("Rempah",       "rempah"),
    ("Peternakan",   "peternakan"),
    ("Perikanan",    "perikanan"),
    ("Lainnya",      "lainnya"),
]


def upgrade() -> None:
    # ── categories ────────────────────────────────────────────────────────────
    op.create_table(
        "categories",
        sa.Column("id",   sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)

    # Seed default categories
    categories_table = sa.table(
        "categories",
        sa.column("id",   sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
    )
    op.bulk_insert(
        categories_table,
        [{"id": str(uuid.uuid4()), "name": name, "slug": slug}
         for name, slug in DEFAULT_CATEGORIES],
    )

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id",          sa.String(36), primary_key=True, nullable=False),
        sa.Column("farmer_id",   sa.String(36),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(36),
                  sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name",        sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price",       sa.Numeric(12, 2), nullable=False),
        sa.Column("unit",        sa.String(30), nullable=False),
        sa.Column("stock",       sa.Integer, nullable=False, server_default="0"),
        sa.Column("image_url",   sa.String(500), nullable=True),
        sa.Column("province",    sa.String(100), nullable=True),
        sa.Column("city",        sa.String(100), nullable=True),
        sa.Column("is_active",   sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_products_farmer_id",   "products", ["farmer_id"])
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_name",        "products", ["name"])
    op.create_index("ix_products_province",    "products", ["province"])


def downgrade() -> None:
    op.drop_table("products")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_table("categories")
