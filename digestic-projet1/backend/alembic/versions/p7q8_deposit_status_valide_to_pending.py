"""BL : variante statut « valide » (sans d) → pending.

Revision ID: p7q8_deposit_valide_to_pending
Revises: o5p6_val_pending
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "p7q8_deposit_valide_to_pending"
down_revision: Union[str, None] = "o5p6_val_pending"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("UPDATE deposits SET status = 'pending' WHERE status = 'valide'"))


def downgrade() -> None:
    op.execute(
        text(
            "UPDATE deposits SET status = 'valide' "
            "WHERE status = 'pending' AND validated_at IS NOT NULL"
        )
    )
