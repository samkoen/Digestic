"""Point de reprise Alembic (révision présente en base sans fichier).

Certaines bases ont `alembic_version` = q8r9_dep_vf_wh_doc après un essai de
migration « VosFactures warehouse doc » retirée du dépôt. Cette révision est un
no-op pour réaligner le graphe ; les colonnes VF associées ne sont pas en ORM.

Revision ID: q8r9_dep_vf_wh_doc
Revises: p7q8_deposit_valide_to_pending
Create Date: 2026-04-28
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "q8r9_dep_vf_wh_doc"
down_revision: Union[str, None] = "p7q8_deposit_valide_to_pending"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
