"""Vue pharmacies : ajouter la colonne city aux réglages en base si absente.

Revision ID: i5j6_pharmacy_view_city
Revises: h3i4_pharmacy_saved_filters
Create Date: 2026-04-26
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i5j6_pharmacy_view_city"
down_revision: Union[str, None] = "h3i4_pharmacy_saved_filters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, visible_column_keys FROM app_table_view_settings "
            "WHERE view_key = 'pharmacies'"
        )
    ).mappings().all()
    for row in rows:
        keys = row["visible_column_keys"]
        rid = row["id"]
        if not isinstance(keys, list) or "city" in keys:
            continue
        new_keys: list[str] = []
        inserted = False
        for k in keys:
            new_keys.append(k)
            if k == "address":
                new_keys.append("city")
                inserted = True
        if not inserted:
            new_keys.append("city")
        conn.execute(
            sa.text(
                "UPDATE app_table_view_settings SET visible_column_keys = "
                "CAST(:payload AS jsonb) WHERE id = :rid"
            ),
            {"payload": json.dumps(new_keys), "rid": rid},
        )


def downgrade() -> None:
    pass
