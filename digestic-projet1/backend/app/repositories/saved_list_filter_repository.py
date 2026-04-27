"""Persistance des préréglages de filtres (plusieurs vues : pharmacies, factures, …)."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import app.db.models as orm


def list_for_user(
    db: Session, user_id: uuid.UUID, view_key: str
) -> list[orm.SavedListFilter]:
    q = (
        select(orm.SavedListFilter)
        .where(
            orm.SavedListFilter.user_id == user_id,
            orm.SavedListFilter.view_key == view_key,
        )
        .order_by(orm.SavedListFilter.updated_at.desc())
    )
    return list(db.execute(q).scalars().all())


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    view_key: str,
    name: str,
    payload: dict,
) -> orm.SavedListFilter:
    row = orm.SavedListFilter(
        id=uuid.uuid4(),
        user_id=user_id,
        view_key=view_key,
        name=name,
        payload=payload,
    )
    db.add(row)
    db.flush()
    return row


def delete_for_user(
    db: Session, user_id: uuid.UUID, view_key: str, filter_id: uuid.UUID
) -> bool:
    r = db.execute(
        delete(orm.SavedListFilter).where(
            orm.SavedListFilter.id == filter_id,
            orm.SavedListFilter.user_id == user_id,
            orm.SavedListFilter.view_key == view_key,
        )
    )
    return (r.rowcount or 0) > 0
