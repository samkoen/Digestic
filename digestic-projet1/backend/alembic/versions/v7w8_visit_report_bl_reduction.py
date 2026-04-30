"""Rapports de visite : réduction BL (pourcentage HT) appliquée au seul bon lié au rapport.

Revision ID: v7w8_visit_report_bl_red
Revises: u5v6_billing_digest01
Create Date: 2026-04-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v7w8_visit_report_bl_red"
down_revision: Union[str, None] = "u5v6_billing_digest01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visit_reports",
        sa.Column(
            "bl_reduction_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("visit_reports", "bl_reduction_percent")
