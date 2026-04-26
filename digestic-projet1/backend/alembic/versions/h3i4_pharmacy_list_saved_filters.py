"""Filtres personnalisés liste pharmacies (par utilisateur).

Revision ID: h3i4_pharmacy_saved_filters
Revises: g1h2_depots_type_qty
Create Date: 2026-04-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "h3i4_pharmacy_saved_filters"
down_revision: Union[str, None] = "g1h2_depots_type_qty"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pharmacy_list_saved_filters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("payload", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pharmacy_list_saved_filters_user_id",
        "pharmacy_list_saved_filters",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pharmacy_list_saved_filters_user_id",
        table_name="pharmacy_list_saved_filters",
    )
    op.drop_table("pharmacy_list_saved_filters")
