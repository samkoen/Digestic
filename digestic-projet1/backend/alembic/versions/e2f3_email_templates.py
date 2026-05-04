"""Modèles d'e-mail HTML configurables par l'admin.

Revision ID: e2f3_email_tpl
Revises: b5c6_dep_vr_null
Create Date: 2026-05-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e2f3_email_tpl"
down_revision: Union[str, None] = "b5c6_dep_vr_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("subject_template", sa.Text(), nullable=False),
        sa.Column("body_html_template", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            name="fk_email_templates_updated_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("template_key", name="uq_email_templates_template_key"),
    )


def downgrade() -> None:
    op.drop_table("email_templates")
