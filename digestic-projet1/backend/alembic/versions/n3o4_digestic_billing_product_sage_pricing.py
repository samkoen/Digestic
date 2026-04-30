"""Prix / TVA produit facturation alignés sur facture Sage type (TVA 5,5 %, PU HT flacon).

Revision ID: n3o4_product_sage_pricing
Revises: l1m2_saved_list_filters_unify
Create Date: 2026-04-27

Référence historique N°172025 (37,80 € HT/u). Voir migration `u5v6_billing_digest01` pour l’alignement
sur la facture type N°171599 (DIGEST01, 21 € HT, TVA 5,5 %).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n3o4_product_sage_pricing"
down_revision: Union[str, None] = "l1m2_saved_list_filters_unify"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Libellé proche de la facture Sage ; à adapter en base si besoin métier
_BILLING_NAME = "Réassort flacons Digestic"
_UNIT_HT = "37.80"
_VAT = "5.5"


def upgrade() -> None:
    bind = op.get_bind()
    r = bind.execute(
        sa.text(
            """
            UPDATE products
            SET wholesale_unit_price = CAST(:u AS NUMERIC(12, 4)),
                vat_rate = CAST(:v AS NUMERIC(5, 2)),
                name = :n
            WHERE is_active IS TRUE AND is_default_for_billing IS TRUE
            """
        ),
        {"u": _UNIT_HT, "v": _VAT, "n": _BILLING_NAME},
    )
    if r.rowcount == 0:
        bind.execute(
            sa.text(
                """
                UPDATE products
                SET wholesale_unit_price = CAST(:u AS NUMERIC(12, 4)),
                    vat_rate = CAST(:v AS NUMERIC(5, 2)),
                    name = :n
                WHERE id = (
                    SELECT id FROM products
                    WHERE is_active IS TRUE
                    ORDER BY is_default_for_billing DESC NULLS LAST, name
                    LIMIT 1
                )
                """
            ),
            {"u": _UNIT_HT, "v": _VAT, "n": _BILLING_NAME},
        )


def downgrade() -> None:
    """Ne restaure pas les anciennes valeurs (souvent 2 € / 20 % en dev)."""
    pass
