from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.domain.billing.due_date import due_date_for_invoice
from app.integrations.vosfactures import get_vosfactures_invoice_issuer
from app.models.delivery_note import DeliveryNote
from app.models.invoice import Invoice
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.product_repository import get_default_billing_product_row


class DeliveryNoteService:
    """Service pour la gestion des bons de livraison."""

    def __init__(
        self,
        repository: DeliveryNoteRepository,
        invoice_repo: InvoiceRepository,
        pharmacy_repo: PharmacyRepository,
        db: Session,
    ):
        self.repository = repository
        self._invoice_repo = invoice_repo
        self._pharm_repo = pharmacy_repo
        self._db = db

    def get_all_delivery_notes(self) -> List[DeliveryNote]:
        return self.repository.find_all()

    def get_delivery_note_by_id(self, note_id: str) -> Optional[DeliveryNote]:
        return self.repository.find_by_id(note_id)

    def create_delivery_note(self, note_data: dict) -> DeliveryNote:
        note_data = dict(note_data)
        note_data["id"] = str(uuid.uuid4())
        note = DeliveryNote.from_dict(note_data)
        return self.repository.create(note)

    def update_delivery_note(self, note_id: str, note_data: dict) -> Optional[DeliveryNote]:
        existing = self.repository.find_by_id(note_id)
        if not existing:
            return None

        for key, value in note_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        existing.updated_at = datetime.now().isoformat()

        return self.repository.update(note_id, existing)

    def mark_as_sent(self, note_id: str) -> Optional[DeliveryNote]:
        return self.update_delivery_note(
            note_id,
            {
                "email_sent": True,
                "email_sent_at": datetime.now().isoformat(),
                "status": "sent",
            },
        )

    def get_delivery_notes_by_pharmacy(self, pharmacy_id: str) -> List[DeliveryNote]:
        return self.repository.find_by_pharmacy(pharmacy_id)

    def get_delivery_notes_by_commercial(self, commercial_id: str) -> List[DeliveryNote]:
        return self.repository.find_by_commercial(commercial_id)

    def issue_invoice_from_delivery_note(
        self, note_id: str, bottles_to_invoice: int, amount: float
    ) -> tuple[Invoice, DeliveryNote | None]:
        """Émet la facture pour tout ou partie du BL : base locale + VosFactures (ou mock)."""
        _ = amount  # conservé pour compatibilité API ; montants calculés depuis le produit
        note = self.repository.find_by_id(note_id)
        if not note:
            raise ValueError("Bon de livraison introuvable")
        note_bc = int(note.bottles_count or 0)
        if bottles_to_invoice <= 0 or bottles_to_invoice > note_bc:
            raise ValueError(
                f"Quantité invalide : indiquez entre 1 et {note_bc} bouteille(s) à facturer."
            )

        product_row = get_default_billing_product_row(self._db)
        if not product_row:
            raise ValueError(
                "Aucun produit actif en base : impossible de facturer (prix / TVA)."
            )

        pharmacy = self._pharm_repo.find_by_id(note.pharmacy_id)
        if not pharmacy:
            raise ValueError("Pharmacie introuvable")

        deposit_row = self._db.get(orm.Deposit, mp.parse_uuid(note.id))
        visit_report_id_str = (
            str(deposit_row.visit_report_id) if deposit_row and deposit_row.visit_report_id else None
        )

        issue_d = date.today()
        try:
            dd = note.delivery_date
            sale_d = (
                mp.parse_date(dd)
                if dd and str(dd).strip()
                else issue_d
            )
        except ValueError:
            sale_d = issue_d
        due = due_date_for_invoice(issue_d, pharmacy.payment_mode)

        pid = product_row.id
        unit_ht = float(product_row.wholesale_unit_price)
        vat_rate = float(product_row.vat_rate)

        full_paying_convert = bottles_to_invoice == note_bc
        free_qty = int(note.free_units_quantity or 0) if full_paying_convert else 0

        lines_spec: list[dict] = []
        mock_lines: list[dict] = []
        total_ht = 0.0
        total_vat = 0.0

        lht = round(bottles_to_invoice * unit_ht, 4)
        lvat = round(lht * (vat_rate / 100.0), 4)
        total_ht += lht
        total_vat += lvat
        lines_spec.append(
            {
                "product_id": str(pid),
                "quantity": bottles_to_invoice,
                "unit_price": unit_ht,
                "vat_rate": vat_rate,
                "is_free_unit": False,
                "discount_percent": 0.0,
                "line_total_ht": lht,
                "reference_unit_price_ht": None,
            }
        )
        mock_lines.append(
            {
                "label": product_row.name,
                "quantity": bottles_to_invoice,
                "unit_price_ht": unit_ht,
                "vat_rate_percent": vat_rate,
                "line_ht": lht,
                "nature": "paying",
            }
        )

        if free_qty > 0:
            lines_spec.append(
                {
                    "product_id": str(pid),
                    "quantity": free_qty,
                    "unit_price": 0.0,
                    "vat_rate": vat_rate,
                    "is_free_unit": True,
                    "discount_percent": 100.0,
                    "line_total_ht": 0.0,
                    "reference_unit_price_ht": unit_ht,
                }
            )
            mock_lines.append(
                {
                    "label": f"{product_row.name} (UG)",
                    "quantity": free_qty,
                    "unit_price_ht": 0.0,
                    "reference_value_ht": unit_ht,
                    "vat_rate_percent": vat_rate,
                    "line_ht": 0.0,
                    "nature": "free_unit",
                }
            )

        totals = {
            "total_ht": round(total_ht, 2),
            "total_vat": round(total_vat, 2),
            "total_ttc": round(total_ht + total_vat, 2),
        }

        inv_num = f"FAC-{issue_d.strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"
        issuer = get_vosfactures_invoice_issuer()
        vf = issuer.issue_vat_invoice(
            draft_invoice_number=inv_num,
            pharmacy=pharmacy,
            issue_date=issue_d,
            sale_date=sale_d,
            due_date=due,
            lines=mock_lines,
            totals=totals,
            billing_type="from_delivery_note",
            deposit_reference=str(note.id),
            currency=str(product_row.currency or "EUR"),
        )

        inv = Invoice(
            id=str(uuid.uuid4()),
            pharmacy_id=note.pharmacy_id,
            invoice_number=vf.invoice_number or inv_num,
            amount=totals["total_ttc"],
            issue_date=issue_d.isoformat(),
            due_date=due.isoformat(),
            sale_date=sale_d.isoformat(),
            status="pending",
            deposit_id=str(note.id),
            visit_report_id=visit_report_id_str,
            billing_type="immediate",
            amount_ht=totals["total_ht"],
            amount_vat=totals["total_vat"],
            amount_ttc=totals["total_ttc"],
            external_provider=vf.provider,
            external_invoice_id=vf.external_id,
            mock_provider_payload=vf.payload,
        )
        created = self._invoice_repo.create(inv, lines=lines_spec)

        remainder = note_bc - bottles_to_invoice
        if remainder > 0:
            note.bottles_count = remainder
            note.updated_at = datetime.now().isoformat()
            next_note = self.repository.update(note.id, note)
        else:
            if self.repository.delete(note.id):
                next_note = None
            else:
                next_note = None

        return created, next_note
