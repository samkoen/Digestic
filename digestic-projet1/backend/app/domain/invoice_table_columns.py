"""Registre des colonnes de la liste factures (clés API, tri, colonnes visibles)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InvoiceTableColumn:
    key: str
    label: str
    sortable: bool
    filterable: bool


_INVOICE_VIEW_KEY = "invoices"

_DEFAULT_VISIBLE: list[str] = [
    "invoiceNumber",
    "pharmacyName",
    "blNumber",
    "amount",
    "issueDate",
    "dueDate",
    "status",
    "daysOverdue",
]

_INVOICE_TABLE_COLUMNS: list[InvoiceTableColumn] = [
    InvoiceTableColumn("invoiceNumber", "N° facture", True, True),
    InvoiceTableColumn("pharmacyName", "Pharmacie", True, True),
    InvoiceTableColumn(
        "blNumber",
        "N° BL",
        True,
        True,
    ),
    InvoiceTableColumn("amount", "Montant (TTC)", True, False),
    InvoiceTableColumn("issueDate", "Date d’émission", True, False),
    InvoiceTableColumn("dueDate", "Date d’échéance", True, False),
    InvoiceTableColumn("status", "Statut", True, True),
    InvoiceTableColumn("daysOverdue", "Jours de retard", True, False),
]

# Tri côté SQL : clés stables (camelCase) alignées requêtes + filtres enregistrés
INVOICE_SORT_KEYS: frozenset[str] = frozenset(
    {c.key for c in _INVOICE_TABLE_COLUMNS if c.sortable}
)


def invoice_table_view_key() -> str:
    return _INVOICE_VIEW_KEY


def default_invoice_visible_keys() -> list[str]:
    return list(_DEFAULT_VISIBLE)


def all_invoice_table_columns() -> list[InvoiceTableColumn]:
    return list(_INVOICE_TABLE_COLUMNS)


def invoice_column_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": c.key,
            "label": c.label,
            "sortable": c.sortable,
            "filterable": c.filterable,
        }
        for c in _INVOICE_TABLE_COLUMNS
    ]


def allowed_invoice_column_keys() -> frozenset[str]:
    return frozenset(c.key for c in _INVOICE_TABLE_COLUMNS)


def normalize_invoice_visible_keys(keys: list[str] | None) -> list[str] | None:
    allowed = allowed_invoice_column_keys()
    if not keys or not isinstance(keys, list):
        return None
    out: list[str] = []
    for k in keys:
        if not isinstance(k, str):
            return None
        if k == "blDeposit":
            k = "blNumber"
        if k not in allowed or k in out:
            return None
        out.append(k)
    return out or None
