"""Pharmacies : réduction commerciale (%) appliquée BL / facture.

Revision ID: t3u4_pharmacy_reduction_pct
Revises: s1t2_dep_bl_number
Create Date: 2026-04-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t3u4_pharmacy_reduction_pct"
down_revision: Union[str, None] = "s1t2_dep_bl_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pharmacies",
        sa.Column(
            "reduction_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("pharmacies", "reduction_percent")
