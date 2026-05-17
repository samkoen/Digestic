"""Calendrier planning par commercial (journées récurrentes + dates fermées).

Revision ID: c9d0_comm_plan_cal
Revises: z8a9_ph_plan_segments
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9d0_comm_plan_cal"
down_revision: Union[str, None] = "z8a9_ph_plan_segments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commercial_planning_off_weekdays",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "commercial_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.UniqueConstraint(
            "commercial_user_id",
            "weekday",
            name="uq_comm_plan_off_weekdays_comm_weekday",
        ),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_comm_plan_weekday_range"),
    )
    op.create_index(
        "ix_comm_plan_off_weekdays_commercial",
        "commercial_planning_off_weekdays",
        ["commercial_user_id"],
    )

    op.create_table(
        "commercial_planning_off_dates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "commercial_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("off_date", sa.Date(), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.UniqueConstraint(
            "commercial_user_id",
            "off_date",
            name="uq_comm_plan_off_dates_comm_date",
        ),
    )
    op.create_index(
        "ix_comm_plan_off_dates_commercial",
        "commercial_planning_off_dates",
        ["commercial_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_comm_plan_off_dates_commercial", table_name="commercial_planning_off_dates")
    op.drop_table("commercial_planning_off_dates")
    op.drop_index("ix_comm_plan_off_weekdays_commercial", table_name="commercial_planning_off_weekdays")
    op.drop_table("commercial_planning_off_weekdays")
