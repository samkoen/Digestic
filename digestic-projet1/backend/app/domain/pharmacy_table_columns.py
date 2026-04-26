"""Registre des colonnes de la liste pharmacies (clé API, libellé, champs requête)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PharmacyTableColumn:
    key: str
    label: str
    sortable: bool
    filterable: bool


_VIEWS_KEY = "pharmacies"

# Clés stables côté front (camelCase) — aligné tri / filtres requêtes.
_DEFAULT_ORDER: list[str] = [
    "name",
    "address",
    "city",
    "commercial",
    "lastVisit",
    "nextVisit",
    "status",
    "rib",
]

_PHARMACY_TABLE_COLUMNS: list[PharmacyTableColumn] = [
    PharmacyTableColumn("name", "Nom", True, True),
    PharmacyTableColumn("address", "Adresse (ligne + CP + ville affichage)", True, True),
    PharmacyTableColumn("city", "Ville", True, True),
    PharmacyTableColumn("postalCode", "Code postal", True, True),
    PharmacyTableColumn("country", "Pays", True, True),
    PharmacyTableColumn("email", "Email", True, True),
    PharmacyTableColumn("phone", "Téléphone", True, True),
    PharmacyTableColumn("pharmacistName", "Titulaire", True, True),
    PharmacyTableColumn("commercial", "Commercial", True, True),
    PharmacyTableColumn("depot", "Dépôt", True, True),
    PharmacyTableColumn("lastVisit", "Dernière visite", True, True),
    PharmacyTableColumn("nextVisit", "Prochaine visite", True, True),
    PharmacyTableColumn("status", "Statut", True, True),
    PharmacyTableColumn("rib", "RIB", True, True),
    PharmacyTableColumn("paymentMode", "Mode de paiement", True, True),
    PharmacyTableColumn("createdAt", "Créée le", True, True),
]


def pharmacy_table_view_key() -> str:
    return _VIEWS_KEY


def default_pharmacy_visible_keys() -> list[str]:
    return list(_DEFAULT_ORDER)


def all_pharmacy_table_columns() -> list[PharmacyTableColumn]:
    return list(_PHARMACY_TABLE_COLUMNS)


def pharmacy_column_definitions() -> list[dict[str, Any]]:
    return [
        {
            "key": c.key,
            "label": c.label,
            "sortable": c.sortable,
            "filterable": c.filterable,
        }
        for c in _PHARMACY_TABLE_COLUMNS
    ]


def allowed_pharmacy_column_keys() -> frozenset[str]:
    return frozenset(c.key for c in _PHARMACY_TABLE_COLUMNS)


# Tri côté SQL : même ensemble de clés que les colonnes triables
PHARMACY_SORT_KEYS: frozenset[str] = frozenset(allowed_pharmacy_column_keys())


def normalize_pharmacy_visible_keys(keys: list[str] | None) -> list[str] | None:
    """Valide l’ordre et le contenu ; None si vide ou clé inconnue."""
    allowed = allowed_pharmacy_column_keys()
    if not keys or not isinstance(keys, list):
        return None
    out: list[str] = []
    for k in keys:
        if not isinstance(k, str) or k not in allowed or k in out:
            return None
        out.append(k)
    return out or None
