"""Dépôts: type, quantité, historique de transferts.

Revision ID: g1h2_depots_type_qty
Revises: f0a1_pharmacy_comments
Create Date: 2026-04-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1h2_depots_type_qty"
down_revision: Union[str, None] = "f0a1_pharmacy_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "warehouses",
        sa.Column(
            "depot_type",
            sa.String(32),
            server_default=sa.text("'secondaire'"),
            nullable=False,
        ),
    )
    op.add_column(
        "warehouses",
        sa.Column(
            "quantity",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_warehouses_depot_type",
        "warehouses",
        "depot_type IN ('central', 'secondaire')",
    )
    op.create_check_constraint(
        "ck_warehouses_quantity_nonnegative",
        "warehouses",
        "quantity >= 0",
    )
    op.execute(
        "UPDATE warehouses SET depot_type = 'central' "
        "WHERE name = 'Entrepot principal'"
    )

    op.create_table(
        "depot_transfers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("from_warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("to_warehouse_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_depot_transfer_qty_positive"),
        sa.CheckConstraint(
            "from_warehouse_id <> to_warehouse_id",
            name="ck_depot_transfer_different_warehouses",
        ),
        sa.ForeignKeyConstraint(
            ["from_warehouse_id"],
            ["warehouses.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["to_warehouse_id"],
            ["warehouses.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_depot_transfers_created_at",
        "depot_transfers",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_depot_transfers_created_at", table_name="depot_transfers")
    op.drop_table("depot_transfers")
    op.drop_constraint("ck_warehouses_quantity_nonnegative", "warehouses", type_="check")
    op.drop_constraint("ck_warehouses_depot_type", "warehouses", type_="check")
    op.drop_column("warehouses", "quantity")
    op.drop_column("warehouses", "depot_type")
