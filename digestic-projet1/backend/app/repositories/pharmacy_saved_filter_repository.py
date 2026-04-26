"""Persistance des filtres liste pharmacies enregistrés par utilisateur."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp


def list_for_user(db: Session, user_id: uuid.UUID) -> list[orm.PharmacyListSavedFilter]:
    q = (
        select(orm.PharmacyListSavedFilter)
        .where(orm.PharmacyListSavedFilter.user_id == user_id)
        .order_by(orm.PharmacyListSavedFilter.updated_at.desc())
    )
    return list(db.execute(q).scalars().all())


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    name: str,
    payload: dict,
) -> orm.PharmacyListSavedFilter:
    row = orm.PharmacyListSavedFilter(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        payload=payload,
    )
    db.add(row)
    db.flush()
    return row


def delete_for_user(
    db: Session, user_id: uuid.UUID, filter_id: uuid.UUID
) -> bool:
    r = db.execute(
        delete(orm.PharmacyListSavedFilter).where(
            orm.PharmacyListSavedFilter.id == filter_id,
            orm.PharmacyListSavedFilter.user_id == user_id,
        )
    )
    return (r.rowcount or 0) > 0


def get_for_user(
    db: Session, user_id: uuid.UUID, filter_id: uuid.UUID
) -> orm.PharmacyListSavedFilter | None:
    q = select(orm.PharmacyListSavedFilter).where(
        orm.PharmacyListSavedFilter.id == filter_id,
        orm.PharmacyListSavedFilter.user_id == user_id,
    )
    return db.execute(q).scalar_one_or_none()
