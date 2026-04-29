"""BL : statut validated (visite) → pending (filtre « En attente »).

Revision ID: o5p6_val_pending
Revises: n3o4_product_sage_pricing
Create Date: 2026-04-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "o5p6_val_pending"
down_revision: Union[str, None] = "n3o4_product_sage_pricing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("UPDATE deposits SET status = 'pending' WHERE status = 'validated'"))


def downgrade() -> None:
    op.execute(
        text(
            "UPDATE deposits SET status = 'validated' "
            "WHERE status = 'pending' AND validated_at IS NOT NULL"
        )
    )
