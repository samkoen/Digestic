"""Adresse utilisée pour les envois transactionnels (BL, factures, relances)."""

from __future__ import annotations

from app.models.pharmacy import Pharmacy


def notification_email_for_pharmacy(pharmacy: Pharmacy) -> str:
    """
    Contact affiché sur la fiche : `pharmacist_email` (owner_email ou email établissement),
    puis repli sur `email` (colonne établissement seule).
    Ne pas inverser : `email` seul peut rester obsolète si le pharmacien a été mis à jour via owner_email.
    """
    return (pharmacy.pharmacist_email or pharmacy.email or "").strip()
