"""Colonnes planning pharmacies (RDV dur, verrouillage manuel).

Revision ID: w2x3_ph_planning
Revises: f4g5_ph_adv_filt
Create Date: 2026-05-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w2x3_ph_planning"
down_revision: Union[str, None] = "f4g5_ph_adv_filt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pharmacies",
        sa.Column("planning_hard_rdv_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "pharmacies",
        sa.Column(
            "planning_manual_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.alter_column(
        "pharmacies",
        "planning_manual_override",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("pharmacies", "planning_manual_override")
    op.drop_column("pharmacies", "planning_hard_rdv_date")
