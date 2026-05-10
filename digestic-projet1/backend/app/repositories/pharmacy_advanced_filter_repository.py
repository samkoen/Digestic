from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp


def list_all(db: Session) -> list[orm.PharmacyAdvancedFilter]:
    q = select(orm.PharmacyAdvancedFilter).order_by(
        orm.PharmacyAdvancedFilter.name.asc(),
        orm.PharmacyAdvancedFilter.updated_at.desc(),
    )
    return list(db.execute(q).scalars().all())


def get_by_id(db: Session, id_str: str) -> orm.PharmacyAdvancedFilter | None:
    try:
        uid = mp.parse_uuid(id_str)
    except ValueError:
        return None
    return db.get(orm.PharmacyAdvancedFilter, uid)


def create_row(
    db: Session, *, name: str, payload: dict[str, Any]
) -> orm.PharmacyAdvancedFilter:
    row = orm.PharmacyAdvancedFilter(
        id=uuid.uuid4(),
        name=name.strip()[:200],
        payload=payload,
    )
    db.add(row)
    db.flush()
    return row


def update_row(
    db: Session, row: orm.PharmacyAdvancedFilter, *, name: str, payload: dict[str, Any]
) -> orm.PharmacyAdvancedFilter:
    row.name = name.strip()[:200]
    row.payload = payload
    db.flush()
    return row


def delete_row(db: Session, row: orm.PharmacyAdvancedFilter) -> None:
    db.delete(row)
