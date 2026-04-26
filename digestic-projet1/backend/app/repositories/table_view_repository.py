"""Persistance des préférences de colonnes (app_table_view_settings)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp


def get_visible_keys_by_view(db: Session, view_key: str) -> list | None:
    q = select(orm.AppTableViewSetting).where(
        orm.AppTableViewSetting.view_key == view_key
    )
    row = db.execute(q).scalars().first()
    if not row or not row.visible_column_keys:
        return None
    return list(row.visible_column_keys)


def upsert_visible_keys(
    db: Session,
    view_key: str,
    column_keys: list[str],
    updated_by_user_id: str,
) -> None:
    try:
        uid = mp.parse_uuid(updated_by_user_id)
    except ValueError as e:
        raise ValueError("user_id invalide") from e
    q = select(orm.AppTableViewSetting).where(
        orm.AppTableViewSetting.view_key == view_key
    )
    row = db.execute(q).scalars().first()
    if row is None:
        row = orm.AppTableViewSetting(
            id=uuid.uuid4(),
            view_key=view_key,
            visible_column_keys=column_keys,
            updated_by_user_id=uid,
        )
        db.add(row)
    else:
        row.visible_column_keys = column_keys
        row.updated_by_user_id = uid
    db.flush()
