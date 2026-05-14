"""Segments planning par pharmacie + révision « manuel » + mode manuel runtime.

Revision ID: z8a9_ph_plan_segments
Revises: y6z7_planning_weights_cfg
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z8a9_ph_plan_segments"
down_revision: Union[str, None] = "y6z7_planning_weights_cfg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_MANUAL_REV_ID = "00000000-0000-4000-8000-000000000001"

_DEFAULT_WEIGHTS = {
    "stock_out": 120.0,
    "stock_low": 55.0,
    "failed_closed": 48.0,
    "failed_other": 22.0,
    "per_day_overdue": 10.0,
    "max_overdue_bonus": 90.0,
    "in_target_week": 72.0,
    "geo_weight": 8.0,
    "fill_radius_km": 14.0,
    "district_density": 6.0,
    "visits_max_per_day": 14,
    "default_cycle_days": 28,
    "orphan_horizon_bonus_days": 10,
}


def upgrade() -> None:
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO planning_weights_revisions (id, revision_number, label, weights, created_at)
            SELECT CAST(:mid AS uuid), 0, :lbl, CAST(:wj AS jsonb), now()
            WHERE NOT EXISTS (
                SELECT 1 FROM planning_weights_revisions WHERE revision_number = 0
            )
            """
        ),
        {
            "mid": _MANUAL_REV_ID,
            "lbl": "__manual_planning__",
            "wj": json.dumps(_DEFAULT_WEIGHTS),
        },
    )

    op.add_column(
        "planning_runtime_settings",
        sa.Column(
            "manual_planning_segment_mode",
            sa.String(length=32),
            nullable=False,
            server_default="inherit",
        ),
    )
    op.create_check_constraint(
        "ck_planning_runtime_manual_segment_mode",
        "planning_runtime_settings",
        "manual_planning_segment_mode IN ('inherit', 'manual_revision')",
    )

    op.create_table(
        "pharmacy_planning_revision_segments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("pharmacy_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("planning_weights_revision_id", sa.Uuid(), nullable=True),
        sa.Column("planning_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "segment_source",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "weights_override_from_request",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.ForeignKeyConstraint(
            ["pharmacy_id"],
            ["pharmacies.id"],
            name="fk_ph_plan_segments_pharmacy",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["planning_weights_revision_id"],
            ["planning_weights_revisions.id"],
            name="fk_ph_plan_segments_revision",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["planning_run_id"],
            ["planning_runs.id"],
            name="fk_ph_plan_segments_run",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "segment_source IN ('auto', 'manual')",
            name="ck_ph_plan_segments_source",
        ),
    )
    op.create_index(
        "ix_ph_plan_segments_pharmacy_valid_from",
        "pharmacy_planning_revision_segments",
        ["pharmacy_id", "valid_from"],
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_ph_plan_segments_one_open
            ON pharmacy_planning_revision_segments (pharmacy_id)
            WHERE valid_to IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_ph_plan_segments_one_open"))
    op.drop_index("ix_ph_plan_segments_pharmacy_valid_from", table_name="pharmacy_planning_revision_segments")
    op.drop_table("pharmacy_planning_revision_segments")
    op.drop_constraint("ck_planning_runtime_manual_segment_mode", "planning_runtime_settings", type_="check")
    op.drop_column("planning_runtime_settings", "manual_planning_segment_mode")
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM planning_weights_revisions WHERE id = CAST(:mid AS uuid)"),
        {"mid": _MANUAL_REV_ID},
    )
