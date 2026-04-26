"""
Modes de paiement (dépôt / pharmacie) : libellés lisibles stockés tels quels en base
(pas d'enum SQL) — filtres et API utilisent le même texte.
"""

from __future__ import annotations

DEFAULT_PHARMACY_PAYMENT_MODE: str = "virement 30 jours"
DEFAULT_VISIT_REPORT_PAYMENT_MODE: str = "virement 30 jours"

CANONICAL_PAYMENT_MODES: tuple[str, ...] = (
    "prélèvement SEPA 30 jours",
    "prélèvement SEPA 60 jours",
    "virement 30 jours",
    "virement 60 jours",
    "dépôt vente",
)

_CANONICAL_LOWER = {m.lower() for m in CANONICAL_PAYMENT_MODES}

# Clés / anciens libellés (API) -> libellé courant
_LEGACY_TO_CANONICAL: dict[str, str] = {
    "virement_30": "virement 30 jours",
    "virement_60": "virement 60 jours",
    "depot_vente": "dépôt vente",
    "sepa_30": "prélèvement SEPA 30 jours",
    "sepa_60": "prélèvement SEPA 60 jours",
    "encaissement sous 30 jours": "virement 30 jours",
    "encaissement sous 60 jours": "virement 60 jours",
    "dépôt-vente": "dépôt vente",
    "dépôt vente": "dépôt vente",
    "depot vente": "dépôt vente",
    "prélèvement sepa 30 jours": "prélèvement SEPA 30 jours",
    "prélèvement sepa 60 jours": "prélèvement SEPA 60 jours",
    "prélevement sepa 30 jours": "prélèvement SEPA 30 jours",
    "prélevement sepa 60 jours": "prélèvement SEPA 60 jours",
}

for m in CANONICAL_PAYMENT_MODES:
    _LEGACY_TO_CANONICAL[m.lower()] = m


def is_prélèvement_sepa(payment_mode: str | None) -> bool:
    s = (payment_mode or "").strip().lower()
    return s.startswith("prélèvement sepa")


def is_depot_vente(payment_mode: str | None) -> bool:
    if not payment_mode or not str(payment_mode).strip():
        return False
    s = " ".join(
        str(payment_mode)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .split()
    )
    return s in ("dépôt vente", "depot vente", "dépôtvente", "depotvente")


def normalize_pharmacy_payment_mode(value: str | None) -> str:
    if not (value and str(value).strip()):
        return DEFAULT_PHARMACY_PAYMENT_MODE
    raw = str(value).strip()
    if raw.lower() in _CANONICAL_LOWER:
        for c in CANONICAL_PAYMENT_MODES:
            if c.lower() == raw.lower():
                return c
    low = raw.lower()
    if low in _LEGACY_TO_CANONICAL:
        return _LEGACY_TO_CANONICAL[low]
    return _LEGACY_TO_CANONICAL.get(low, raw)


def payment_mode_for_api(stored: str | None) -> str:
    """DB -> réponse API : libellé canonique si reconnue, sinon telle quelle."""
    if not (stored and str(stored).strip()):
        return DEFAULT_PHARMACY_PAYMENT_MODE
    s = str(stored).strip()
    if s.lower() in _CANONICAL_LOWER:
        for c in CANONICAL_PAYMENT_MODES:
            if c.lower() == s.lower():
                return c
    return normalize_pharmacy_payment_mode(s)
