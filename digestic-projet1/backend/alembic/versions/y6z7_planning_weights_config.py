"""Paramètres planning versionnés (JSON) + révision active + historique des runs.

Révisions des **poids du moteur de planning** (distinct de la note terrain « v1 »).

Revision ID: y6z7_planning_weights_cfg
Revises: x4y5_feeling_rating
"""

from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "y6z7_planning_weights_cfg"
down_revision: Union[str, None] = "x4y5_feeling_rating"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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
    rid = uuid.uuid4()

    op.create_table(
        "planning_weights_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_planning_weights_revisions_created_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("revision_number", name="uq_planning_weights_revisions_number"),
    )
    op.create_index(
        "ix_planning_weights_revisions_created_at",
        "planning_weights_revisions",
        ["created_at"],
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO planning_weights_revisions (id, revision_number, label, weights, created_at)
            VALUES (:id, 1, :label, CAST(:weights AS jsonb), now())
            """
        ),
        {
            "id": rid,
            "label": "Seed — équivalent valeurs code `PlanningWeights`",
            "weights": json.dumps(_DEFAULT_WEIGHTS),
        },
    )

    op.create_table(
        "planning_runtime_settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("active_revision_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["active_revision_id"],
            ["planning_weights_revisions.id"],
            name="fk_planning_runtime_active_revision",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_planning_runtime_settings"),
        sa.CheckConstraint("id = 1", name="ck_planning_runtime_settings_singleton"),
    )
    bind.execute(
        sa.text(
            "INSERT INTO planning_runtime_settings (id, active_revision_id) VALUES (1, :rid)"
        ),
        {"rid": rid},
    )

    op.create_table(
        "planning_runs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("active_only", sa.Boolean(), nullable=False),
        sa.Column("scope_commercial_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("active_revision_id_at_run", sa.Uuid(), nullable=True),
        sa.Column("weights_request_override", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("weights_effective", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assignments_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=True),
        sa.Column("skipped_manual_override_count", sa.Integer(), nullable=False),
        sa.Column("triggered_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["active_revision_id_at_run"],
            ["planning_weights_revisions.id"],
            name="fk_planning_runs_active_revision",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["triggered_by_user_id"],
            ["users.id"],
            name="fk_planning_runs_triggered_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_planning_runs_created_at", "planning_runs", ["created_at"])
    op.create_index(
        "ix_planning_runs_active_revision_id_at_run",
        "planning_runs",
        ["active_revision_id_at_run"],
    )


def downgrade() -> None:
    op.drop_index("ix_planning_runs_active_revision_id_at_run", table_name="planning_runs")
    op.drop_index("ix_planning_runs_created_at", table_name="planning_runs")
    op.drop_table("planning_runs")
    op.drop_table("planning_runtime_settings")
    op.drop_index("ix_planning_weights_revisions_created_at", table_name="planning_weights_revisions")
    op.drop_table("planning_weights_revisions")
