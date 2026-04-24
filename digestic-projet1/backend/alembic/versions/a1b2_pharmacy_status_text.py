"""pharmacy_status texte (actif, desactive, standby…) remplace active bool

Revision ID: a1b2_pharmacy_status
Revises: 9d2e_pharmacy_active
Create Date: 2026-04-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a1b2_pharmacy_status"
down_revision: Union[str, None] = "9d2e_pharmacy_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}

    if "pharmacy_status" in cols:
        if "active" in cols:
            op.drop_column("pharmacies", "active")
        return

    op.add_column(
        "pharmacies",
        sa.Column(
            "pharmacy_status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'actif'"),
        ),
    )
    if "active" in cols:
        op.execute(
            """
            UPDATE pharmacies
            SET pharmacy_status = CASE
                WHEN active IS FALSE THEN 'desactive'
                ELSE 'actif'
            END
            """
        )
    op.alter_column("pharmacies", "pharmacy_status", server_default=None)
    if "active" in cols:
        op.drop_column("pharmacies", "active")


def downgrade() -> None:
    bind = op.get_bind()
    ins = inspect(bind)
    cols = {c["name"] for c in ins.get_columns("pharmacies")}

    if "active" not in cols:
        op.add_column(
            "pharmacies",
            sa.Column(
                "active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
    if "pharmacy_status" in cols:
        op.execute(
            """
            UPDATE pharmacies
            SET active = (pharmacy_status IN ('actif', 'standby'))
            """
        )
        op.alter_column("pharmacies", "active", server_default=None)
        op.drop_column("pharmacies", "pharmacy_status")
