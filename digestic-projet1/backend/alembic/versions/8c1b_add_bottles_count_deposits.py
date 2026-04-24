"""add bottles_count to deposits (idempotent)

Revision ID: 8c1b_add_bottles
Revises: 5eb306a15ae0
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "8c1b_add_bottles"
down_revision: Union[str, None] = "5eb306a15ae0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("deposits")}
    if "bottles_count" not in cols:
        op.add_column(
            "deposits",
            sa.Column("bottles_count", sa.Integer(), nullable=False, server_default="0"),
        )
        op.alter_column("deposits", "bottles_count", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("deposits")}
    if "bottles_count" in cols:
        op.drop_column("deposits", "bottles_count")
