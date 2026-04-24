"""pharmacies.active (actif / inactif)

Revision ID: 9d2e_pharmacy_active
Revises: 8c1b_add_bottles
Create Date: 2026-04-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "9d2e_pharmacy_active"
down_revision: Union[str, None] = "8c1b_add_bottles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}
    if "active" not in cols:
        op.add_column(
            "pharmacies",
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
        op.alter_column("pharmacies", "active", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}
    if "active" in cols:
        op.drop_column("pharmacies", "active")
