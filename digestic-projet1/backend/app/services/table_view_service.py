"""Préférences de visibilité des colonnes (par vue métier)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.domain.delivery_note_table_columns import (
    default_delivery_note_visible_keys,
    delivery_note_column_definitions,
    delivery_notes_table_view_key,
    normalize_delivery_note_visible_keys,
)
from app.domain.invoice_table_columns import (
    allowed_invoice_column_keys,
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


def _ensure_invoice_bl_number_column(visible: list[str]) -> list[str]:
    """Ajoute la colonne N° BL si elle manque (préférences enregistrées avant l’évolution)."""
    allowed = allowed_invoice_column_keys()
    out = [k for k in visible if k in allowed]
    if "blNumber" in allowed and "blNumber" not in out:
        if "pharmacyName" in out:
            i = out.index("pharmacyName") + 1
            out.insert(i, "blNumber")
        else:
            out.append("blNumber")
    return out


@dataclass(frozen=True)
class _TableViewSpec:
    definitions: Callable[[], list[dict[str, Any]]]
    normalize: Callable[[list[str] | None], list[str] | None]
    default_visible: Callable[[], list[str]]
    post_visible: Callable[[list[str]], list[str]] | None = None


_TABLE_VIEW_SPECS: dict[str, _TableViewSpec] = {
    pharmacy_table_view_key(): _TableViewSpec(
        definitions=pharmacy_column_definitions,
        normalize=normalize_pharmacy_visible_keys,
        default_visible=default_pharmacy_visible_keys,
    ),
    invoice_table_view_key(): _TableViewSpec(
        definitions=invoice_column_definitions,
        normalize=normalize_invoice_visible_keys,
        default_visible=default_invoice_visible_keys,
        post_visible=_ensure_invoice_bl_number_column,
    ),
    delivery_notes_table_view_key(): _TableViewSpec(
        definitions=delivery_note_column_definitions,
        normalize=normalize_delivery_note_visible_keys,
        default_visible=default_delivery_note_visible_keys,
    ),
}


def get_table_view(db: Session, view_key: str) -> dict[str, Any]:
    spec = _TABLE_VIEW_SPECS.get(view_key)
    if not spec:
        raise KeyError(view_key)
    raw = tv_repo.get_visible_keys_by_view(db, view_key)
    visible = spec.normalize(raw) or spec.default_visible()
    if spec.post_visible:
        visible = spec.post_visible(visible)
    return {
        "viewKey": view_key,
        "definition": spec.definitions(),
        "visibleColumnKeys": visible,
    }


def set_table_view(
    db: Session, view_key: str, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    spec = _TABLE_VIEW_SPECS.get(view_key)
    if not spec:
        raise KeyError(view_key)
    valid = spec.normalize(column_keys)
    if not valid or len(valid) < 1:
        raise ValueError("Au moins une colonne requise, clés inconnues ou doublons")
    tv_repo.upsert_visible_keys(db, view_key, valid, admin_user_id)
    return {"viewKey": view_key, "visibleColumnKeys": valid}


def get_pharmacies_table_view(db: Session) -> dict[str, Any]:
    return get_table_view(db, pharmacy_table_view_key())


def set_pharmacies_table_view(
    db: Session, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    return set_table_view(db, pharmacy_table_view_key(), column_keys, admin_user_id)


def get_invoices_table_view(db: Session) -> dict[str, Any]:
    return get_table_view(db, invoice_table_view_key())


def set_invoices_table_view(
    db: Session, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    return set_table_view(db, invoice_table_view_key(), column_keys, admin_user_id)


def get_delivery_notes_table_view(db: Session) -> dict[str, Any]:
    return get_table_view(db, delivery_notes_table_view_key())


def set_delivery_notes_table_view(
    db: Session, column_keys: list[str], admin_user_id: str
) -> dict[str, Any]:
    return set_table_view(db, delivery_notes_table_view_key(), column_keys, admin_user_id)
