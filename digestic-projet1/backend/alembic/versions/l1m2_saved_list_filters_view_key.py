"""Filtres enregistrés : view_key (pharmacies, invoices) et table unifiée saved_list_filters.

Revision ID: l1m2_saved_list_filters_unify
Revises: k9l0_product_catalog_fields
Create Date: 2026-04-27
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l1m2_saved_list_filters_unify"
down_revision: Union[str, None] = "k9l0_product_catalog_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pharmacy_list_saved_filters",
        sa.Column(
            "view_key",
            sa.String(32),
            server_default=sa.text("'pharmacies'"),
            nullable=False,
        ),
    )
    op.execute("UPDATE pharmacy_list_saved_filters SET view_key = 'pharmacies'")
    op.create_index(
        "ix_saved_list_filters_user_view",
        "pharmacy_list_saved_filters",
        ["user_id", "view_key"],
    )
    op.rename_table("pharmacy_list_saved_filters", "saved_list_filters")
    op.execute(
        "ALTER TABLE saved_list_filters ALTER COLUMN view_key DROP DEFAULT"
    )


def downgrade() -> None:
    op.rename_table("saved_list_filters", "pharmacy_list_saved_filters")
    op.drop_index("ix_saved_list_filters_user_view", table_name="pharmacy_list_saved_filters")
    op.drop_column("pharmacy_list_saved_filters", "view_key")
