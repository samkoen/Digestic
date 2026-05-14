"""Visit reports: feeling_rating (note ressenti commercial 1–5).

Revision ID: x4y5_feeling_rating
Revises: w2x3_ph_planning
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x4y5_feeling_rating"
down_revision: Union[str, None] = "w2x3_ph_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visit_reports",
        sa.Column("feeling_rating", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_visit_reports_feeling_rating_range",
        "visit_reports",
        "feeling_rating IS NULL OR (feeling_rating >= 1 AND feeling_rating <= 5)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_visit_reports_feeling_rating_range", "visit_reports", type_="check")
    op.drop_column("visit_reports", "feeling_rating")
