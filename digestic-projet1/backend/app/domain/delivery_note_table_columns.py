"""Registre des colonnes de la liste bons de livraison / dépôts (table `deposits`)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DeliveryNoteTableColumn:
    key: str
    label: str
    sortable: bool
    filterable: bool


_VIEW_KEY = "delivery_notes"

_DEFAULT_VISIBLE: list[str] = [
    "pharmacyName",
    "deliveryDate",
    "blNumber",
    "bottlesCount",
    "commercial",
    "status",
    "linkedInvoices",
]

_COLUMNS: list[DeliveryNoteTableColumn] = [
    DeliveryNoteTableColumn("pharmacyName", "Pharmacie", True, True),
    DeliveryNoteTableColumn("deliveryDate", "Date dépôt", True, True),
    DeliveryNoteTableColumn("blNumber", "N° BL", True, False),
    DeliveryNoteTableColumn("bottlesCount", "Bouteilles", True, False),
    DeliveryNoteTableColumn("freeUnits", "UG", True, False),
    DeliveryNoteTableColumn("commercial", "Commercial", True, True),
    DeliveryNoteTableColumn("status", "Statut", True, True),
    DeliveryNoteTableColumn(
        "linkedInvoices",
        "Facture(s)",
        False,
        False,
    ),
    DeliveryNoteTableColumn("isDepositSale", "Dépôt-vente", True, True),
    DeliveryNoteTableColumn("sageReference", "Réf. Sage / externe", True, True),
    DeliveryNoteTableColumn("depositId", "ID dépôt (Digestic)", True, True),
    DeliveryNoteTableColumn("emailSent", "Email envoyé", True, True),
]


def delivery_notes_table_view_key() -> str:
    return _VIEW_KEY


def default_delivery_note_visible_keys() -> list[str]:
    return list(_DEFAULT_VISIBLE)


def all_delivery_note_table_columns() -> list[DeliveryNoteTableColumn]:
    return list(_COLUMNS)


def delivery_note_column_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": c.key,
            "label": c.label,
            "sortable": c.sortable,
            "filterable": c.filterable,
        }
        for c in _COLUMNS
    ]


def allowed_delivery_note_column_keys() -> frozenset[str]:
    return frozenset(c.key for c in _COLUMNS)


DELIVERY_NOTE_SORT_KEYS: frozenset[str] = frozenset(
    {c.key for c in _COLUMNS if c.sortable}
)


def normalize_delivery_note_visible_keys(keys: list[str] | None) -> list[str] | None:
    allowed = allowed_delivery_note_column_keys()
    if not keys or not isinstance(keys, list):
        return None
    out: list[str] = []
    for k in keys:
        if not isinstance(k, str) or k not in allowed or k in out:
            return None
        out.append(k)
    return out or None
