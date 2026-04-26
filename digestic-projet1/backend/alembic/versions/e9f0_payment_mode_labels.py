"""Libellés modes de paiement (texte en base) + largeur colonne.

Revision ID: e9f0_payment_mode_labels
Revises: d7e8_visit_report_extras
Create Date: 2026-04-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9f0_payment_mode_labels"
down_revision: Union[str, None] = "d7e8_visit_report_extras"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "pharmacies",
        "payment_mode",
        existing_type=sa.String(32),
        type_=sa.String(80),
        existing_nullable=False,
        server_default=None,
    )

    # Données historiques -> libellés affichables
    op.execute(
        sa.text(
            """
            UPDATE pharmacies SET payment_mode = 'virement 30 jours'
            WHERE payment_mode IN ('virement_30', 'encaissement sous 30 jours');
            UPDATE pharmacies SET payment_mode = 'virement 60 jours'
            WHERE payment_mode IN ('virement_60', 'encaissement sous 60 jours');
            UPDATE pharmacies SET payment_mode = 'dépôt vente'
            WHERE payment_mode IN ('depot_vente', 'dépôt-vente', 'dépôt vente', 'depot vente');
            UPDATE pharmacies SET payment_mode = 'prélèvement SEPA 30 jours'
            WHERE payment_mode IN ('sepa_30', 'prélèvement sepa 30 jours', 'prélevement sepa 30 jours');
            UPDATE pharmacies SET payment_mode = 'prélèvement SEPA 60 jours'
            WHERE payment_mode IN ('sepa_60', 'prélèvement sepa 60 jours', 'prélevement sepa 60 jours');
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE visit_reports SET payment_mode = 'virement 30 jours'
            WHERE payment_mode IN ('virement_30', 'encaissement sous 30 jours');
            UPDATE visit_reports SET payment_mode = 'virement 60 jours'
            WHERE payment_mode IN ('virement_60', 'encaissement sous 60 jours');
            UPDATE visit_reports SET payment_mode = 'dépôt vente'
            WHERE payment_mode IN ('depot_vente', 'dépôt-vente', 'dépôt vente', 'depot vente');
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "pharmacies",
        "payment_mode",
        existing_type=sa.String(80),
        type_=sa.String(32),
        existing_nullable=False,
    )
