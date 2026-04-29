"""Dépôts : numéro de bon BL- (affichage + facture VosFactures).

Revision ID: s1t2_dep_bl_number
Revises: q8r9_dep_vf_wh_doc
Create Date: 2026-04-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "s1t2_dep_bl_number"
down_revision: Union[str, None] = "q8r9_dep_vf_wh_doc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deposits",
        sa.Column("bl_number", sa.String(48), nullable=True),
    )
    op.create_index("ix_deposits_bl_number", "deposits", ["bl_number"], unique=False)
    # Rétrofill : BL-AAAAMMJJ-XXXXXXXX à partir de la date de dépôt et de l’id
    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE deposits
            SET bl_number = 'BL-' || to_char(delivery_date, 'YYYYMMDD') || '-'
                || upper(substring(replace(id::text, '-', '') from 1 for 8))
            WHERE bl_number IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_deposits_bl_number", table_name="deposits")
    op.drop_column("deposits", "bl_number")
