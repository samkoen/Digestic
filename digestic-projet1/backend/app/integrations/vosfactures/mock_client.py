"""Client factice imitant la réponse API vosfactures.fr (aucun appel HTTP)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.integrations.vosfactures.types import VosFacturesInvoiceResult
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
