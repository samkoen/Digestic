"""Suppression colonne pharmacies.classification

Revision ID: b3c4_pharmacy_no_classif
Revises: a1b2_pharmacy_status
Create Date: 2026-04-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "b3c4_pharmacy_no_classif"
down_revision: Union[str, None] = "a1b2_pharmacy_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}
    if "classification" in cols:
        op.drop_column("pharmacies", "classification")


def downgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}
    if "classification" not in cols:
        op.add_column(
            "pharmacies",
            sa.Column("classification", sa.String(20), nullable=False, server_default="C"),
        )
        op.alter_column("pharmacies", "classification", server_default=None)
