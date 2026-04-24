"""Données référentielles minimales (ex. entrepôt par défaut)."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm

DEFAULT_WAREHOUSE_NAME = "Entrepot principal"


def get_or_create_default_warehouse_id(db: Session) -> uuid.UUID:
    w = db.execute(
        select(orm.Warehouse).where(orm.Warehouse.name == DEFAULT_WAREHOUSE_NAME)
    ).scalar_one_or_none()
    if w is not None:
        return w.id
    w = orm.Warehouse(
        name=DEFAULT_WAREHOUSE_NAME,
        country="FR",
        is_active=True,
    )
    db.add(w)
    db.flush()
    return w.id
