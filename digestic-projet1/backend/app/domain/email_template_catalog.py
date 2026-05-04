"""Catalogue des modèles d'e-mail configurables par l’admin."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailTemplateCatalogEntry:
    key: str
    label_fr: str
    description_fr: str
    placeholders: tuple[str, ...]


# Clés stables utilisées dans le code métier ; de nouvelles lignes peuvent être ajoutées en base hors catalogue.
TEMPLATE_DELIVERY_NOTE_SEND = "delivery_note_send"
TEMPLATE_INVOICE_SEND = "invoice_send"
TEMPLATE_INVOICE_UNPAID_REMINDER = "invoice_unpaid_reminder"

KNOWN_TEMPLATE_KEYS = frozenset({
    TEMPLATE_DELIVERY_NOTE_SEND,
    TEMPLATE_INVOICE_SEND,
    TEMPLATE_INVOICE_UNPAID_REMINDER,
})

EMAIL_TEMPLATE_CATALOG: tuple[EmailTemplateCatalogEntry, ...] = (
    EmailTemplateCatalogEntry(
        key=TEMPLATE_DELIVERY_NOTE_SEND,
        label_fr="Envoi d’un bon de livraison",
        description_fr="Courriel envoyé lors de l’envoi d’un BL à la pharmacie.",
        placeholders=(
            "pharmacy_name",
            "bl_number",
            "delivery_date",
        ),
    ),
    EmailTemplateCatalogEntry(
        key=TEMPLATE_INVOICE_SEND,
        label_fr="Envoi d’une facture",
        description_fr="Courriel envoyé lors de l’envoi manuel d’une facture.",
        placeholders=(
            "pharmacy_name",
            "invoice_number",
            "invoice_amount",
            "invoice_date",
            "due_date",
        ),
    ),
    EmailTemplateCatalogEntry(
        key=TEMPLATE_INVOICE_UNPAID_REMINDER,
        label_fr="Rappel de facture impayée",
        description_fr=(
            "Pour relances automatiques ou manuelles sur les factures en retard "
            "(ex. tâche planifiée à brancher ultérieurement)."
        ),
        placeholders=(
            "pharmacy_name",
            "invoice_number",
            "invoice_amount",
            "invoice_date",
            "due_date",
            "days_overdue",
        ),
    ),
)


def catalog_entry_for_key(template_key: str) -> EmailTemplateCatalogEntry | None:
    for e in EMAIL_TEMPLATE_CATALOG:
        if e.key == template_key:
            return e
    return None
