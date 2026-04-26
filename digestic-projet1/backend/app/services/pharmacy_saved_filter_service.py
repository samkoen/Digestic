"""Filtres enregistrés (préréglages) pour la liste pharmacies."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domain.pharmacy_table_columns import PHARMACY_SORT_KEYS
from app.db import mappers as mp
from app.repositories import pharmacy_saved_filter_repository as repo

def _empty_filter_dict() -> dict[str, Any]:
    return {
        "name": "",
        "address": "",
        "city": [],
        "postalCodes": [],
        "country": "",
        "email": "",
        "phone": "",
        "pharmacistName": "",
        "commercial": [],
        "depot": [],
        "lastVisit": "",
        "nextVisit": "",
        "status": "",
        "paymentMode": [],
        "rib": "",
        "created": "",
    }


_MULTI_VALUE_KEYS = frozenset(
    {"postalCodes", "commercial", "paymentMode", "city", "depot"}
)
_ALLOWED_FILTER_KEYS = frozenset(_empty_filter_dict().keys())


def _sanitize_filters(raw: Any) -> dict[str, Any]:
    out = _empty_filter_dict()
    if not isinstance(raw, dict):
        return out
    for k in _ALLOWED_FILTER_KEYS:
        if k not in raw:
            continue
        v = raw[k]
        if k in _MULTI_VALUE_KEYS:
            if isinstance(v, list):
                out[k] = [str(x).strip() for x in v if str(x).strip()]
            elif isinstance(v, str) and v.strip():
                out[k] = [v.strip()]
            elif v is None:
                out[k] = []
            else:
                t = str(v).strip()
                out[k] = [t] if t else []
        elif isinstance(v, str):
            out[k] = v
        elif v is None:
            out[k] = ""
        else:
            out[k] = str(v)
    return out


def _sanitize_sort_payload(order_by: Any, order: Any) -> tuple[str, str]:
    ob = str(order_by).strip() if order_by is not None else "name"
    if ob not in PHARMACY_SORT_KEYS:
        ob = "name"
    o = str(order).lower().strip() if order is not None else "asc"
    if o not in ("asc", "desc"):
        o = "asc"
    return ob, o


def build_payload(body: dict[str, Any] | None) -> dict[str, Any]:
    b = body or {}
    filters = _sanitize_filters(b.get("filters"))
    order_by, order = _sanitize_sort_payload(b.get("orderBy"), b.get("order"))
    return {"filters": filters, "orderBy": order_by, "order": order}


def parse_create_body(body: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    if not body:
        raise ValueError("Nom requis")
    raw_name = body.get("name")
    if raw_name is None:
        raise ValueError("Nom requis")
    name = str(raw_name).strip()
    if not name:
        raise ValueError("Nom requis")
    if len(name) > 160:
        name = name[:160]
    payload = build_payload(body)
    return name, payload


def row_to_api(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "payload": row.payload,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_for_user(db: Session, user_id_str: str) -> list[dict[str, Any]]:
    uid = mp.parse_uuid(user_id_str)
    rows = repo.list_for_user(db, uid)
    return [row_to_api(r) for r in rows]


def create(db: Session, user_id_str: str, body: dict[str, Any] | None) -> dict[str, Any]:
    uid = mp.parse_uuid(user_id_str)
    name, payload = parse_create_body(body)
    row = repo.create(db, user_id=uid, name=name, payload=payload)
    return row_to_api(row)


def delete_for_user(db: Session, user_id_str: str, filter_id_str: str) -> bool:
    uid = mp.parse_uuid(user_id_str)
    try:
        fid = mp.parse_uuid(filter_id_str)
    except ValueError:
        return False
    return repo.delete_for_user(db, uid, fid)
