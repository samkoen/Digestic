"""Définitions de filtres avancés liste pharmacies (conditions champ / op / valeur).

Revision ID: f4g5_ph_adv_filt
Revises: e2f3_email_tpl
Create Date: 2026-05-05
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f4g5_ph_adv_filt"
down_revision: Union[str, None] = "e2f3_email_tpl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pharmacy_advanced_filters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pharmacy_advanced_filters_name",
        "pharmacy_advanced_filters",
        ["name"],
    )


def downgrade() -> None:
    op.drop_index("ix_pharmacy_advanced_filters_name", table_name="pharmacy_advanced_filters")
    op.drop_table("pharmacy_advanced_filters")
