"""Produits : EAN et produit par défaut pour la facturation des visites.

Revision ID: k9l0_product_catalog_fields
Revises: j7k8_billing_visit_flow
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k9l0_product_catalog_fields"
down_revision: Union[str, None] = "j7k8_billing_visit_flow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("ean", sa.String(20), nullable=True))
    op.add_column(
        "products",
        sa.Column(
            "is_default_for_billing",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_products_ean", "products", ["ean"], unique=False)
    op.create_index(
        "ix_products_default_billing",
        "products",
        ["is_default_for_billing"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_default_billing", table_name="products")
    op.drop_index("ix_products_ean", table_name="products")
    op.drop_column("products", "is_default_for_billing")
    op.drop_column("products", "ean")
