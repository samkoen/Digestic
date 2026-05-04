"""Émission et consultation des avoirs (VosFactures)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.integrations.vosfactures import get_vosfactures_invoice_issuer
from app.integrations.vosfactures.config import vosfactures_is_configured
from app.integrations.vosfactures.http_client import (
    VosFacturesApiClient,
    _parse_invoice_from_create_response,
    totals_abs_from_vf_document,
)
from app.repositories.credit_note_repository import CreditNoteRepository
from app.repositories.invoice_repository import (
    InvoiceRepository,
    invoice_line_ht_total,
    invoice_line_rounded_ttc,
)


def _parse_vf_date(val: Any) -> date | None:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _vf_tax_public(tax_pct: float) -> str | int | float:
    t = float(tax_pct)
    if abs(t - round(t)) < 1e-9:
        return int(round(t))
    return round(t, 2)


def _vf_money(amount: float) -> str:
    return f"{round(float(amount), 2):.2f}"


class CreditNoteService:
    """Avoir total ou partiel via API VosFactures (kind=correction) + enregistrement local."""

    def __init__(self, db: Session):
        self._db = db
        self._invoices = InvoiceRepository(db)
        self._credit_notes = CreditNoteRepository(db)

    def list_for_invoice(self, invoice_id: str) -> list[dict[str, Any]]:
        return self._credit_notes.list_by_source_invoice(invoice_id)

    def issue_total_credit_note(self, invoice_id: str, correction_reason: str) -> dict[str, Any]:
        inv = self._invoices.find_by_id(invoice_id)
        if not inv:
            raise ValueError("Facture introuvable")
        ext_id = (inv.external_invoice_id or "").strip()
        prov = (inv.external_provider or "").strip().lower()
        if prov not in ("vosfactures", "vosfactures_mock"):
            raise ValueError("Seules les factures émises via VosFactures (ou mock) peuvent avoir un avoir.")
        if not ext_id:
            raise ValueError("Facture sans identifiant VosFactures : impossible de créer l'avoir.")
        reason = (correction_reason or "").strip()
        if len(reason) < 3:
            raise ValueError("Le motif de l'avoir doit contenir au moins 3 caractères.")

        issuer = get_vosfactures_invoice_issuer()
        st = (inv.status or "").strip().lower()
        if st in ("credited", "cancelled"):
            raise ValueError(
                "Cette facture ne peut plus recevoir d'avoir : statut définitif "
                f"({inv.status}).",
            )

        vf_result = issuer.issue_total_credit_note(
            from_external_invoice_id=ext_id,
            correction_reason=reason,
        )

        vf_payload = vf_result.payload
        ht: float | None = None
        vat_amt: float | None = None
        ttc: float | None = None
        issue_d: date | None = None

        raw = vf_payload.get("vosfactures_response") if isinstance(vf_payload, dict) else None
        if isinstance(raw, dict):
            parsed = _parse_invoice_from_create_response(raw)
            if isinstance(parsed, dict):
                ht, vat_amt, ttc = totals_abs_from_vf_document(parsed)
                issue_d = _parse_vf_date(parsed.get("issue_date") or parsed.get("created_at"))

        if prov == "vosfactures_mock" or ttc is None:
            ttc = float(inv.amount_ttc) if inv.amount_ttc is not None else float(inv.amount)
            if inv.amount_ht is not None:
                ht = float(inv.amount_ht)
            if inv.amount_vat is not None:
                vat_amt = float(inv.amount_vat)
            elif ht is not None and ttc is not None:
                vat_amt = round(ttc - ht, 2)

        issue_d = issue_d or date.today()
        cn_num = vf_result.credit_note_number or f"AV-{issue_d.strftime('%Y%m%d')}-{ext_id}"

        cn = self._credit_notes.create(
            pharmacy_id=inv.pharmacy_id,
            source_invoice_id=invoice_id,
            credit_note_number=str(cn_num)[:64],
            issue_date=issue_d,
            amount_ttc=float(ttc),
            amount_ht=ht,
            amount_vat=vat_amt,
            reason=reason,
            external_provider=vf_result.provider,
            external_credit_note_id=vf_result.external_id,
            mock_provider_payload=dict(vf_payload) if isinstance(vf_payload, dict) else None,
            credit_scope="full",
        )

        inv.status = "credited"
        inv.days_overdue = 0
        inv.updated_at = datetime.now().isoformat()
        if self._invoices.update(invoice_id, inv) is None:
            raise ValueError("Mise à jour de la facture après avoir impossible.")
        return cn

    def issue_partial_credit_note(
        self,
        invoice_id: str,
        correction_reason: str,
        partial_lines: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Avoir partiel : positions correction VosFactures + lignes locales (quantités créditées)."""
        inv = self._invoices.find_by_id(invoice_id)
        if not inv:
            raise ValueError("Facture introuvable")
        ext_id = (inv.external_invoice_id or "").strip()
        prov = (inv.external_provider or "").strip().lower()
        if prov not in ("vosfactures", "vosfactures_mock"):
            raise ValueError("Seules les factures émises via VosFactures (ou mock) peuvent avoir un avoir.")
        if not ext_id:
            raise ValueError("Facture sans identifiant VosFactures : impossible de créer l'avoir.")
        reason = (correction_reason or "").strip()
        if len(reason) < 3:
            raise ValueError("Le motif de l'avoir doit contenir au moins 3 caractères.")

        st = (inv.status or "").strip().lower()
        if st in ("credited", "cancelled"):
            raise ValueError(
                "Cette facture ne peut plus recevoir d'avoir : statut définitif "
                f"({inv.status}).",
            )

        merged: dict[str, int] = defaultdict(int)
        for pl in partial_lines:
            lid = str(pl.get("invoice_line_id", "")).strip()
            merged[lid] += int(pl.get("quantity", 0))
        if not merged:
            raise ValueError("Aucune ligne d'avoir partiel indiquée.")

        try:
            inv_uuid = mp.parse_uuid(invoice_id)
        except ValueError as e:
            raise ValueError("Identifiant facture invalide") from e

        credited = self._invoices.credited_quantities_per_invoice_line(inv_uuid)
        positions: list[dict[str, Any]] = []
        persist_lines: list[dict[str, Any]] = []
        sum_delta_ht = 0.0
        sum_delta_ttc = 0.0

        for line_id_str, qty_req in merged.items():
            if qty_req <= 0:
                raise ValueError("Les quantités à créditer doivent être positives.")
            try:
                line_uuid = mp.parse_uuid(line_id_str)
            except ValueError as e:
                raise ValueError(f"Ligne facture invalide : {line_id_str}") from e

            li_row = self._db.get(orm.InvoiceLine, line_uuid)
            if not li_row or li_row.invoice_id != inv_uuid:
                raise ValueError(f"Ligne {line_id_str} introuvable pour cette facture.")
            if li_row.is_free_unit:
                raise ValueError(
                    "Les unités gratuites ne peuvent pas faire l'objet d'un avoir partiel ligne à ligne."
                )

            qb = int(li_row.quantity or 0)
            if qb <= 0:
                raise ValueError(f"Ligne {line_id_str} : quantité facturée nulle.")
            already = int(credited.get(li_row.id, 0) or 0)
            rem = qb - already
            if qty_req > rem:
                raise ValueError(
                    f"Ligne produit : impossible de créditer {qty_req} unité(s) "
                    f"({rem} restante(s) après avoirs précédents)."
                )

            prod = self._db.get(orm.Product, li_row.product_id)
            label = (prod.name if prod else "Produit").strip() or "Produit"
            pcode = (prod.code or "").strip() if prod else ""

            qa = qb - qty_req
            ttc_b = invoice_line_rounded_ttc(li_row)
            ttc_a = round(ttc_b * (qa / qb), 2) if qb > 0 else 0.0
            ht_b = invoice_line_ht_total(li_row)
            ht_a = round(ht_b * (qa / qb), 4) if qb > 0 else 0.0
            delta_ttc = round(ttc_b - ttc_a, 2)
            delta_ht = round(ht_b - ht_a, 4)
            sum_delta_ttc += delta_ttc
            sum_delta_ht += delta_ht

            tax_f = _vf_tax_public(float(li_row.vat_rate))
            pos: dict[str, Any] = {
                "name": label,
                "quantity": -int(qty_req),
                "total_price_gross": _vf_money(-delta_ttc),
                "tax": tax_f,
                "kind": "correction",
                "correction_before_attributes": {
                    "name": label,
                    "quantity": str(qb),
                    "total_price_gross": _vf_money(ttc_b),
                    "tax": tax_f,
                    "kind": "correction_before",
                },
                "correction_after_attributes": {
                    "name": label,
                    "quantity": str(qa),
                    "total_price_gross": _vf_money(ttc_a),
                    "tax": tax_f,
                    "kind": "correction_after",
                },
            }
            if pcode:
                pos["code"] = pcode
                pos["correction_before_attributes"]["code"] = pcode
                pos["correction_after_attributes"]["code"] = pcode
            positions.append(pos)

            persist_lines.append(
                {
                    "invoice_line_id": str(li_row.id),
                    "product_id": str(li_row.product_id),
                    "quantity": int(qty_req),
                    "unit_price": float(li_row.unit_price),
                    "vat_rate": float(li_row.vat_rate),
                    "is_free_unit": False,
                }
            )

        issuer = get_vosfactures_invoice_issuer()
        vf_result = issuer.issue_partial_credit_note(
            from_external_invoice_id=ext_id,
            correction_reason=reason,
            positions=positions,
            lang="fr",
        )

        vf_payload = vf_result.payload
        ht: float | None = None
        vat_amt: float | None = None
        ttc: float | None = None
        issue_d: date | None = None

        raw = vf_payload.get("vosfactures_response") if isinstance(vf_payload, dict) else None
        if isinstance(raw, dict):
            parsed = _parse_invoice_from_create_response(raw)
            if isinstance(parsed, dict):
                ht, vat_amt, ttc = totals_abs_from_vf_document(parsed)
                issue_d = _parse_vf_date(parsed.get("issue_date") or parsed.get("created_at"))

        if prov == "vosfactures_mock" or ttc is None:
            ttc = round(sum_delta_ttc, 2)
            ht = round(sum_delta_ht, 4)
            vat_amt = round(ttc - (ht or 0), 2)

        issue_d = issue_d or date.today()
        cn_num = vf_result.credit_note_number or f"AVP-{issue_d.strftime('%Y%m%d')}-{ext_id}"

        return self._credit_notes.create(
            pharmacy_id=inv.pharmacy_id,
            source_invoice_id=invoice_id,
            credit_note_number=str(cn_num)[:64],
            issue_date=issue_d,
            amount_ttc=float(ttc or 0),
            amount_ht=ht,
            amount_vat=vat_amt,
            reason=reason,
            external_provider=vf_result.provider,
            external_credit_note_id=vf_result.external_id,
            mock_provider_payload=dict(vf_payload) if isinstance(vf_payload, dict) else None,
            credit_scope="partial",
            line_rows=persist_lines,
        )

    def fetch_credit_note_pdf(self, credit_note_id: str) -> tuple[bytes, str] | None:
        row = self._credit_notes.find_by_id(credit_note_id)
        if not row:
            return None
        prov = (row.external_provider or "").strip().lower()
        ext_cn = (row.external_credit_note_id or "").strip()
        if prov != "vosfactures" or not ext_cn:
            return None
        if not vosfactures_is_configured():
            return None
        pdf = VosFacturesApiClient().fetch_invoice_pdf(ext_cn)
        base = (row.credit_note_number or credit_note_id).strip()
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in base)[:120]
        filename = f"{safe or 'avoir'}.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        return pdf, filename
