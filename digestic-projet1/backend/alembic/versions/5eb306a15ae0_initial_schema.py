"""initial_schema

Revision ID: 5eb306a15ae0
Revises:
Create Date: 2026-04-23 20:19:14.818357

Schéma aligné sur app.db.models (snapshot initial). Les révisions suivantes
préféreront op.add_column / autogenerate pour les évolutions.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "5eb306a15ae0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.base import Base
    from app.db import models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.db.base import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
