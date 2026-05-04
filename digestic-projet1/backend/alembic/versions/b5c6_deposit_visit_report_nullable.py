"""Nullable deposits.visit_report_id pour BL hors rapport de visite (admin).

Revision ID: b5c6_dep_vr_null
Revises: z1a2_cn_partial_ln
Create Date: 2026-04-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "b5c6_dep_vr_null"
down_revision: Union[str, None] = "z1a2_cn_partial_ln"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_NAME_NEW = "fk_deposits_visit_report_id_standalone"


def _drop_visit_report_fk() -> str | None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    names: list[str] = []
    for fk in insp.get_foreign_keys("deposits"):
        if fk.get("constrained_columns") == ["visit_report_id"]:
            names.append(fk["name"])
    for name in names:
        op.drop_constraint(name, "deposits", type_="foreignkey")
    return names[0] if names else None


def upgrade() -> None:
    _drop_visit_report_fk()
    op.alter_column(
        "deposits",
        "visit_report_id",
        existing_type=UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        FK_NAME_NEW,
        "deposits",
        "visit_reports",
        ["visit_report_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM deposits WHERE visit_report_id IS NULL"))
    op.drop_constraint(FK_NAME_NEW, "deposits", type_="foreignkey")
    op.alter_column(
        "deposits",
        "visit_report_id",
        existing_type=UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        FK_NAME_NEW,
        "deposits",
        "visit_reports",
        ["visit_report_id"],
        ["id"],
        ondelete="CASCADE",
    )
