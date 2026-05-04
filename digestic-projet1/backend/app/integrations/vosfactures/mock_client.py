"""Client factice imitant la réponse API vosfactures.fr (aucun appel HTTP)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.integrations.vosfactures.types import (
    VosFacturesCreditNoteResult,
    VosFacturesInvoiceResult,
)
from app.models.pharmacy import Pharmacy

PROVIDER_KEY = "vosfactures_mock"


class VosFacturesMockClient:
    def issue_vat_invoice(
        self,
        *,
        draft_invoice_number: str,
        pharmacy: Pharmacy | None,
        issue_date: date,
        sale_date: date,
        due_date: date,
        lines: list[dict[str, Any]],
        totals: dict[str, float],
        billing_type: str,
        internal_deposit_id: str | None,
        invoice_public_reference: str | None = None,
        currency: str = "EUR",
        digestic_bl_number: str | None = None,
    ) -> VosFacturesInvoiceResult:
        _ = pharmacy, currency
        external_id = f"MOCK-VF-{uuid.uuid4().hex[:12].upper()}"
        ph_name = pharmacy.name if pharmacy else ""
        document = {
            "invoice_number": draft_invoice_number,
            "external_provider_invoice_id": external_id,
            "seller": {"name": "Digestic", "country": "FR"},
            "customer": {"name": ph_name, "id": (pharmacy.id if pharmacy else None)},
            "dates": {
                "issue": issue_date.isoformat(),
                "sale": sale_date.isoformat(),
                "due": due_date.isoformat(),
            },
            "billing_type": billing_type,
            "internal_deposit_id": internal_deposit_id,
            "invoice_public_reference": (invoice_public_reference or "").strip() or None,
            "digestic_bl_number": (digestic_bl_number or "").strip() or None,
            "lines": lines,
            "totals": totals,
            "legal_mentions_fr": [
                "TVA applicable selon la législation en vigueur.",
                "Document généré par mock vosfactures (phase développement).",
            ],
        }
        return VosFacturesInvoiceResult(
            provider=PROVIDER_KEY,
            external_id=external_id,
            invoice_number=draft_invoice_number,
            payload=document,
        )

    def issue_total_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
    ) -> VosFacturesCreditNoteResult:
        _ = from_external_invoice_id
        external_id = f"MOCK-VF-COR-{uuid.uuid4().hex[:12].upper()}"
        num = f"AV-MOCK-{uuid.uuid4().hex[:8].upper()}"
        document = {
            "credit_note_number": num,
            "external_provider_correction_id": external_id,
            "correction_reason": (correction_reason or "").strip() or "Avoir",
            "legal_mentions_fr": [
                "Document d’avoir généré par mock VosFactures (développement).",
            ],
        }
        return VosFacturesCreditNoteResult(
            provider=PROVIDER_KEY,
            external_id=external_id,
            credit_note_number=num,
            payload=document,
        )

    def issue_partial_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
        positions: list[dict[str, Any]],
        lang: str = "fr",
    ) -> VosFacturesCreditNoteResult:
        _ = from_external_invoice_id, lang, positions
        external_id = f"MOCK-VF-CORP-{uuid.uuid4().hex[:12].upper()}"
        num = f"AVP-MOCK-{uuid.uuid4().hex[:8].upper()}"
        document = {
            "credit_note_number": num,
            "external_provider_correction_id": external_id,
            "correction_reason": (correction_reason or "").strip() or "Avoir partiel",
            "legal_mentions_fr": [
                "Avoir partiel généré par mock VosFactures (développement).",
            ],
        }
        return VosFacturesCreditNoteResult(
            provider=PROVIDER_KEY,
            external_id=external_id,
            credit_note_number=num,
            payload=document,
        )
