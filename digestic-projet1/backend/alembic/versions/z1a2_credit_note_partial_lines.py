"""Avoirs partiels : scope sur credit_notes ; lien lignes facture sources sur credit_note_lines.

Revision ID: z1a2_cn_partial_ln
Revises: v7w8_visit_report_bl_red
Create Date: 2026-04-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "z1a2_cn_partial_ln"
down_revision: Union[str, None] = "v7w8_visit_report_bl_red"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "credit_notes",
        sa.Column(
            "credit_scope",
            sa.String(16),
            nullable=False,
            server_default="full",
        ),
    )
    op.create_check_constraint(
        "ck_credit_notes_credit_scope",
        "credit_notes",
        "credit_scope IN ('full', 'partial')",
    )

    op.add_column(
        "credit_note_lines",
        sa.Column("source_invoice_line_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_credit_note_line_source_invoice_line",
        "credit_note_lines",
        "invoice_lines",
        ["source_invoice_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_credit_note_lines_source_invoice_line_id",
        "credit_note_lines",
        ["source_invoice_line_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_credit_note_lines_source_invoice_line_id", table_name="credit_note_lines")
    op.drop_constraint("fk_credit_note_line_source_invoice_line", "credit_note_lines", type_="foreignkey")
    op.drop_column("credit_note_lines", "source_invoice_line_id")
    op.drop_constraint("ck_credit_notes_credit_scope", "credit_notes", type_="check")
    op.drop_column("credit_notes", "credit_scope")
