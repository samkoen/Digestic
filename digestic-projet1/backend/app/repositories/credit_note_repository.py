"""Persistance des avoirs (liés facture source + VosFactures)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import app.db.models as orm
from app.db import mappers as mp


def _cn_line_preview(line: orm.CreditNoteLine) -> dict[str, Any]:
    return {
        "product_id": str(line.product_id),
        "quantity": int(line.quantity),
        "unit_price": float(line.unit_price),
        "vat_percent": float(line.vat_rate),
        "is_free_unit": bool(line.is_free_unit),
        "source_invoice_line_id": str(line.source_invoice_line_id)
        if line.source_invoice_line_id
        else None,
    }


def _credit_note_to_dict(row: orm.CreditNote) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "pharmacy_id": str(row.pharmacy_id),
        "source_invoice_id": str(row.source_invoice_id) if row.source_invoice_id else None,
        "credit_note_number": row.credit_note_number,
        "credit_scope": getattr(row, "credit_scope", None) or "full",
        "issue_date": row.issue_date.isoformat() if row.issue_date else None,
        "amount_ttc": float(row.amount_ttc),
        "amount_ht": float(row.amount_ht) if row.amount_ht is not None else None,
        "amount_vat": float(row.amount_vat) if row.amount_vat is not None else None,
        "status": row.status,
        "reason": row.reason,
        "external_provider": row.external_provider,
        "external_credit_note_id": row.external_credit_note_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class CreditNoteRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_by_id(self, id_: str) -> orm.CreditNote | None:
        try:
            cid = mp.parse_uuid(id_)
        except ValueError:
            return None
        return self._db.get(orm.CreditNote, cid)

    def list_by_source_invoice(self, invoice_id: str) -> list[dict[str, Any]]:
        try:
            iid = mp.parse_uuid(invoice_id)
        except ValueError:
            return []
        rows = (
            self._db.execute(
                select(orm.CreditNote)
                .where(orm.CreditNote.source_invoice_id == iid)
                .options(selectinload(orm.CreditNote.lines))
                .order_by(orm.CreditNote.issue_date.desc(), orm.CreditNote.created_at.desc())
            )
            .scalars()
            .all()
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            d = _credit_note_to_dict(r)
            if (d.get("credit_scope") or "full") == "partial" and getattr(r, "lines", None):
                d["lines"] = [_cn_line_preview(li) for li in r.lines]
            out.append(d)
        return out

    def create(
        self,
        *,
        pharmacy_id: str,
        source_invoice_id: str,
        credit_note_number: str,
        issue_date: date,
        amount_ttc: float,
        amount_ht: float | None,
        amount_vat: float | None,
        reason: str | None,
        external_provider: str | None,
        external_credit_note_id: str | None,
        mock_provider_payload: dict[str, Any] | None,
        status: str = "issued",
        credit_scope: str = "full",
        line_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        cs = str(credit_scope or "full").strip().lower()
        if cs not in ("full", "partial"):
            cs = "full"
        row = orm.CreditNote(
            id=uuid.uuid4(),
            pharmacy_id=mp.parse_uuid(pharmacy_id),
            source_invoice_id=mp.parse_uuid(source_invoice_id),
            credit_note_number=credit_note_number,
            issue_date=issue_date,
            amount_ttc=amount_ttc,
            amount_ht=amount_ht,
            amount_vat=amount_vat,
            status=status,
            reason=reason,
            external_provider=external_provider,
            external_credit_note_id=external_credit_note_id,
            mock_provider_payload=mock_provider_payload,
            credit_scope=cs,
        )
        self._db.add(row)
        self._db.flush()
        if line_rows:
            for lr in line_rows:
                self._db.add(
                    orm.CreditNoteLine(
                        id=uuid.uuid4(),
                        credit_note_id=row.id,
                        product_id=mp.parse_uuid(lr["product_id"]),
                        quantity=int(lr["quantity"]),
                        unit_price=float(lr["unit_price"]),
                        vat_rate=float(lr["vat_rate"]),
                        is_free_unit=bool(lr.get("is_free_unit", False)),
                        source_invoice_line_id=(
                            mp.parse_uuid(lr["invoice_line_id"])
                            if lr.get("invoice_line_id")
                            else None
                        ),
                    )
                )
            self._db.flush()
        return _credit_note_to_dict(row)
