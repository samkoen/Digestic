"""Table pharmacy_comments (notes sur une pharmacie).

Revision ID: f0a1_pharmacy_comments
Revises: e9f0_payment_mode_labels
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f0a1_pharmacy_comments"
down_revision: Union[str, None] = "e9f0_payment_mode_labels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pharmacy_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pharmacy_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["pharmacy_id"],
            ["pharmacies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pharmacy_comments_pharmacy_id", "pharmacy_comments", ["pharmacy_id"]
    )
    op.create_index(
        "ix_pharmacy_comments_created_at", "pharmacy_comments", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_pharmacy_comments_created_at", table_name="pharmacy_comments")
    op.drop_index("ix_pharmacy_comments_pharmacy_id", table_name="pharmacy_comments")
    op.drop_table("pharmacy_comments")
