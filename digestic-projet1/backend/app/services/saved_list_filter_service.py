"""Préréglages de filtres enregistrés par vue (pharmacies, factures, …)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domain.invoice_table_columns import INVOICE_SORT_KEYS
from app.domain.pharmacy_table_columns import PHARMACY_SORT_KEYS
from app.db import mappers as mp
from app.repositories import saved_list_filter_repository as repo

VIEW_PHARMACIES = "pharmacies"
VIEW_INVOICES = "invoices"
ALLOWED_VIEWS: frozenset[str] = frozenset({VIEW_PHARMACIES, VIEW_INVOICES})

# --- Pharmacies (même logique qu’ex-pharmacy_saved_filter_service) ---

def _empty_pharmacy_filter_dict() -> dict[str, Any]:
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


_PHARM_MULTI = frozenset(
    {"postalCodes", "commercial", "paymentMode", "city", "depot"}
)
_PHARM_ALLOWED = frozenset(_empty_pharmacy_filter_dict().keys())


def _sanitize_pharmacy_filters(raw: Any) -> dict[str, Any]:
    out = _empty_pharmacy_filter_dict()
    if not isinstance(raw, dict):
        return out
    for k in _PHARM_ALLOWED:
        if k not in raw:
            continue
        v = raw[k]
        if k in _PHARM_MULTI:
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


def _order_dir(order: Any) -> str:
    o = str(order).lower().strip() if order is not None else "asc"
    return o if o in ("asc", "desc") else "asc"


def _pharmacy_sort_payload(order_by: Any, order: Any) -> tuple[str, str]:
    ob = str(order_by).strip() if order_by is not None else "name"
    if ob not in PHARMACY_SORT_KEYS:
        ob = "name"
    return ob, _order_dir(order)


def _build_pharmacy_payload(body: dict[str, Any] | None) -> dict[str, Any]:
    b = body or {}
    filters = _sanitize_pharmacy_filters(b.get("filters"))
    ob, o = _pharmacy_sort_payload(b.get("orderBy"), b.get("order"))
    return {"filters": filters, "orderBy": ob, "order": o}


# --- Factures (liste paginée, alignée colonnes) ---

def _empty_invoice_filter_dict() -> dict[str, Any]:
    return {
        "invoiceNumber": "",
        "pharmacyName": "",
        "pharmacyId": "",
        "status": "",
        "overdueOnly": False,
        "overdueMinDays": 30,
    }


_INV_FILTER_ALLOWED = frozenset(_empty_invoice_filter_dict().keys())


def _sanitize_invoice_filters(raw: Any) -> dict[str, Any]:
    out = _empty_invoice_filter_dict()
    if not isinstance(raw, dict):
        return out
    for k in _INV_FILTER_ALLOWED:
        if k not in raw:
            continue
        v = raw[k]
        if k in ("overdueOnly",):
            if v is True or v is False:
                out[k] = v
            elif isinstance(v, str):
                out[k] = v.strip().lower() in ("1", "true", "yes", "oui", "y")
        elif k == "overdueMinDays":
            try:
                d = int(v)
                out[k] = max(0, min(d, 3650))
            except (TypeError, ValueError):
                out[k] = 30
        elif k in ("invoiceNumber", "pharmacyName", "pharmacyId", "status"):
            out[k] = str(v or "").strip() if v is not None else ""
    return out


def _invoice_sort_payload(order_by: Any, order: Any) -> tuple[str, str]:
    ob = str(order_by).strip() if order_by is not None else "issueDate"
    if ob not in INVOICE_SORT_KEYS:
        ob = "issueDate"
    return ob, _order_dir(order)


def _build_invoice_payload(body: dict[str, Any] | None) -> dict[str, Any]:
    b = body or {}
    filters = _sanitize_invoice_filters(b.get("filters"))
    ob, o = _invoice_sort_payload(b.get("orderBy"), b.get("order"))
    return {"filters": filters, "orderBy": ob, "order": o}


def build_payload_for_view(
    view_key: str, body: dict[str, Any] | None
) -> dict[str, Any]:
    if view_key == VIEW_PHARMACIES:
        return _build_pharmacy_payload(body)
    if view_key == VIEW_INVOICES:
        return _build_invoice_payload(body)
    raise ValueError("vue inconnue")


def parse_create_body(
    view_key: str, body: dict[str, Any] | None
) -> tuple[str, dict[str, Any]]:
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
    payload = build_payload_for_view(view_key, body)
    return name, payload


def row_to_api(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "payload": row.payload,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_for_user(db: Session, user_id_str: str, view_key: str) -> list[dict[str, Any]]:
    if view_key not in ALLOWED_VIEWS:
        raise ValueError("vue non autorisée")
    uid = mp.parse_uuid(user_id_str)
    rows = repo.list_for_user(db, uid, view_key)
    return [row_to_api(r) for r in rows]


def create(
    db: Session, user_id_str: str, view_key: str, body: dict[str, Any] | None
) -> dict[str, Any]:
    if view_key not in ALLOWED_VIEWS:
        raise ValueError("vue non autorisée")
    uid = mp.parse_uuid(user_id_str)
    name, payload = parse_create_body(view_key, body)
    row = repo.create(db, user_id=uid, view_key=view_key, name=name, payload=payload)
    return row_to_api(row)


def delete_for_user(
    db: Session, user_id_str: str, view_key: str, filter_id_str: str
) -> bool:
    if view_key not in ALLOWED_VIEWS:
        raise ValueError("vue non autorisée")
    uid = mp.parse_uuid(user_id_str)
    try:
        fid = mp.parse_uuid(filter_id_str)
    except ValueError:
        return False
    return repo.delete_for_user(db, uid, view_key, fid)
