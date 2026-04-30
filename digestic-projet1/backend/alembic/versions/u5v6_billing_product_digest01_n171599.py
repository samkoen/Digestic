"""Produit facturation défaut aligné facture Digestic / Sage (ex. Pharmacie Plateau N°171599).

Revision ID: u5v6_billing_digest01
Revises: t3u4_pharmacy_reduction_pct
Create Date: 2026-04-30

Référence PDF : DIGEST01 — DIGESTIC 60 GELULES ; PU HT 21,00 € ; TVA 5,5 % (C55).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "u5v6_billing_digest01"
down_revision: Union[str, None] = "t3u4_pharmacy_reduction_pct"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODE = "DIGEST01"
_NAME = "DIGESTIC 60 GELULES"
_UNIT_HT = "21.00"
_VAT = "5.50"


def upgrade() -> None:
    bind = op.get_bind()
    r = bind.execute(
        sa.text(
            """
            UPDATE products
            SET code = :code,
                name = :n,
                wholesale_unit_price = CAST(:u AS NUMERIC(12, 4)),
                vat_rate = CAST(:v AS NUMERIC(5, 2))
            WHERE is_active IS TRUE AND is_default_for_billing IS TRUE
            """
        ),
        {"code": _CODE, "n": _NAME, "u": _UNIT_HT, "v": _VAT},
    )
    if r.rowcount == 0:
        bind.execute(
            sa.text(
                """
                UPDATE products
                SET code = :code,
                    name = :n,
                    wholesale_unit_price = CAST(:u AS NUMERIC(12, 4)),
                    vat_rate = CAST(:v AS NUMERIC(5, 2))
                WHERE id = (
                    SELECT id FROM products
                    WHERE is_active IS TRUE
                    ORDER BY is_default_for_billing DESC NULLS LAST, name
                    LIMIT 1
                )
                """
            ),
            {"code": _CODE, "n": _NAME, "u": _UNIT_HT, "v": _VAT},
        )


def downgrade() -> None:
    """Ne rétablit pas les valeurs précédentes (nombreuses références possibles)."""
    pass
