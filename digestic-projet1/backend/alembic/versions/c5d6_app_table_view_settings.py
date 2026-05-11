"""Table app_table_view_settings : préférences de colonnes par vue (tableau).

Revision ID: c5d6_table_views
Revises: b3c4_pharmacy_no_classif
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5d6_table_views"
down_revision: Union[str, None] = "b3c4_pharmacy_no_classif"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée la table si absente (bases déjà partiellement alignées ou reprise après échec)."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "app_table_view_settings" in insp.get_table_names(schema=None):
        return
    op.create_table(
        "app_table_view_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("view_key", sa.String(64), nullable=False),
        sa.Column("visible_column_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("view_key", name="uq_app_table_view_settings_view_key"),
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS app_table_view_settings"))
