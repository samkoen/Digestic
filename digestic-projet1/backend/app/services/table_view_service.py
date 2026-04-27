"""Préférences de visibilité des colonnes (par vue métier)."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domain.invoice_table_columns import (
    default_invoice_visible_keys,
    invoice_column_definitions,
    invoice_table_view_key,
    normalize_invoice_visible_keys,
)
from app.domain.pharmacy_table_columns import (
    default_pharmacy_visible_keys,
    normalize_pharmacy_visible_keys,
    pharmacy_column_definitions,
    pharmacy_table_view_key,
)
from app.repositories import table_view_repository as tv_repo


def get_pharmacies_table_view(db: Session) -> dict[str, Any]:
    key = pharmacy_table_view_key()
    raw = tv_repo.get_visible_keys_by_view(db, key)
    visible = (
        normalize_pharmacy_visible_keys(raw) or default_pharmacy_visible_keys()
    )
    return {
        "viewKey": key,
        "definition": pharmacy_column_definitions(),
        "visibleColumnKeys": visible,
    }


def set_pharmacies_table_view(
    db: Session, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    key = pharmacy_table_view_key()
    valid = normalize_pharmacy_visible_keys(column_keys)
    if not valid or len(valid) < 1:
        raise ValueError("Au moins une colonne requise, clés inconnues ou doublons")
    tv_repo.upsert_visible_keys(db, key, valid, admin_user_id)
    return {
        "viewKey": key,
        "visibleColumnKeys": valid,
    }


def get_invoices_table_view(db: Session) -> dict[str, Any]:
    key = invoice_table_view_key()
    raw = tv_repo.get_visible_keys_by_view(db, key)
    visible = (
        normalize_invoice_visible_keys(raw) or default_invoice_visible_keys()
    )
    return {
        "viewKey": key,
        "definition": invoice_column_definitions(),
        "visibleColumnKeys": visible,
    }


def set_invoices_table_view(
    db: Session, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    key = invoice_table_view_key()
    valid = normalize_invoice_visible_keys(column_keys)
    if not valid or len(valid) < 1:
        raise ValueError("Au moins une colonne requise, clés inconnues ou doublons")
    tv_repo.upsert_visible_keys(db, key, valid, admin_user_id)
    return {
        "viewKey": key,
        "visibleColumnKeys": valid,
    }
