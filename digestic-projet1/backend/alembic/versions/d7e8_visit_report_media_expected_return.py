"""Rapport de visite : médias (voix, photo, vidéo) + semaine de retour prévue (ISO).

Revision ID: d7e8_visit_report_extras
Revises: c5d6_table_views
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7e8_visit_report_extras"
down_revision: Union[str, None] = "c5d6_table_views"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visit_reports",
        sa.Column("expected_return_iso_year", sa.Integer(), nullable=True),
    )
    op.add_column(
        "visit_reports",
        sa.Column("expected_return_iso_week", sa.Integer(), nullable=True),
    )
    op.add_column("visit_reports", sa.Column("voice_note_url", sa.Text(), nullable=True))
    op.add_column("visit_reports", sa.Column("photo_note_url", sa.Text(), nullable=True))
    op.add_column("visit_reports", sa.Column("video_note_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("visit_reports", "video_note_url")
    op.drop_column("visit_reports", "photo_note_url")
    op.drop_column("visit_reports", "voice_note_url")
    op.drop_column("visit_reports", "expected_return_iso_week")
    op.drop_column("visit_reports", "expected_return_iso_year")
