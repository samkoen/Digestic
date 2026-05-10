from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import pharmacy_advanced_filter_repository as repo
from app.repositories.pharmacy_advanced_filter_engine import (
    sanitize_pharmacy_advanced_filter_payload,
)


def row_to_api(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "payload": row.payload,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_filters(db: Session) -> list[dict[str, Any]]:
    rows = repo.list_all(db)
    return [row_to_api(r) for r in rows]


def get_one(db: Session, id_str: str) -> dict[str, Any] | None:
    row = repo.get_by_id(db, id_str)
    return row_to_api(row) if row else None


def create_filter(db: Session, body: dict[str, Any] | None) -> dict[str, Any]:
    b = body or {}
    name = str(b.get("name") or "").strip()
    if not name:
        raise ValueError("Nom requis")
    payload = sanitize_pharmacy_advanced_filter_payload(b.get("payload"))
    row = repo.create_row(db, name=name, payload=payload)
    db.flush()
    return row_to_api(row)


def update_filter(
    db: Session, id_str: str, body: dict[str, Any] | None
) -> dict[str, Any] | None:
    row = repo.get_by_id(db, id_str)
    if not row:
        return None
    b = body or {}
    name = str(b.get("name") or "").strip()
    if not name:
        raise ValueError("Nom requis")
    payload = sanitize_pharmacy_advanced_filter_payload(b.get("payload"))
    repo.update_row(db, row, name=name, payload=payload)
    db.flush()
    return row_to_api(row)


def delete_filter(db: Session, id_str: str) -> bool:
    row = repo.get_by_id(db, id_str)
    if not row:
        return False
    repo.delete_row(db, row)
    return True
