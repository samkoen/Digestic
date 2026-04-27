import uuid
from datetime import date
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.domain.invoice_table_columns import INVOICE_SORT_KEYS
from app.models.invoice import Invoice
from app.pagination import PageResult, offset_for_page, normalize_page_input


def _order_clause(sort: str, order: str, i: type[orm.Invoice], p: type[orm.Pharmacy]):
    """Tri SQL (camelCase -> colonnes, avec pharmacie)."""
    desc_ = (order or "asc").lower() == "desc"
    s = sort if sort in INVOICE_SORT_KEYS else "issueDate"
    col: Any
    if s == "pharmacyName":
        col = p.name
    elif s == "issueDate":
        col = i.issue_date
    elif s == "dueDate":
        col = i.due_date
    elif s == "invoiceNumber":
        col = i.invoice_number
    elif s == "amount":
        col = i.amount
    elif s == "status":
        col = i.status
    else:
        col = i.days_overdue
    return col.desc() if desc_ else col.asc()


class InvoiceRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[Invoice]:
        rows = self._db.execute(select(orm.Invoice)).scalars().all()
        return [mp.invoice_orm_to_domain(r) for r in rows]

    def search_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "issueDate",
        order: str = "asc",
        status: str | None = None,
        invoice_number: str | None = None,
        pharmacy_id: str | None = None,
        pharmacy_name: str | None = None,
        overdue_only: bool = False,
        overdue_min_days: int = 0,
    ) -> PageResult[tuple[Invoice, str | None]]:
        p1, ps = normalize_page_input(page, page_size)
        off = offset_for_page(p1, ps)
        i, ph = orm.Invoice, orm.Pharmacy
        today = date.today()
        skey = sort if sort in INVOICE_SORT_KEYS else "issueDate"

        base = select(i, ph.name).select_from(i).join(ph, i.pharmacy_id == ph.id)
        conds: list[Any] = []
        if status and str(status).strip():
            conds.append(i.status == str(status).strip())
        if invoice_number and str(invoice_number).strip():
            qn = f"%{str(invoice_number).strip()}%"
            conds.append(i.invoice_number.ilike(qn))
        if pharmacy_id and str(pharmacy_id).strip():
            try:
                pid = mp.parse_uuid(str(pharmacy_id).strip())
                conds.append(i.pharmacy_id == pid)
            except ValueError:
                pass
        if pharmacy_name and str(pharmacy_name).strip():
            qph = f"%{str(pharmacy_name).strip()}%"
            conds.append(ph.name.ilike(qph))
        if overdue_only:
            dmin = max(0, int(overdue_min_days))
            # PG : current_date - date = nb de jours (entier)
            conds.append(i.status != "paid")
            conds.append(i.due_date < today)
            conds.append((func.current_date() - i.due_date) >= dmin)

        where = and_(*conds) if conds else None
        if where is not None:
            base = base.where(where)

        count_q = select(func.count()).select_from(i).join(ph, i.pharmacy_id == ph.id)
        if where is not None:
            count_q = count_q.where(where)
        total = int(self._db.execute(count_q).scalar() or 0)

        ob = _order_clause(skey, order, i, ph)
        page_q = base.order_by(ob).offset(off).limit(ps)
        raw_rows = self._db.execute(page_q).all()
        items: list[tuple[Invoice, str | None]] = []
        for row in raw_rows:
            inv_row, pname = row[0], row[1]
            items.append((mp.invoice_orm_to_domain(inv_row), str(pname) if pname is not None else None))
        return PageResult(
            items=items,
            total=total,
            page=p1,
            page_size=ps,
        )

    def find_by_id(self, id_: str) -> Optional[Invoice]:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Invoice, iid)
        return mp.invoice_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[Invoice]:
        q = select(orm.Invoice)
        for k, v in kwargs.items():
            if k == "pharmacy_id" and v is not None:
                v = mp.parse_uuid(v)
            if k == "sage_reference":
                k = "reference_external"
            if not hasattr(orm.Invoice, k):
                continue
            q = q.where(getattr(orm.Invoice, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.invoice_orm_to_domain(r) for r in rows]

    def find_by_pharmacy(self, pharmacy_id: str) -> list[Invoice]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def find_overdue(self, days: int = 30) -> list[Invoice]:
        return [
            inv
            for inv in self.find_all()
            if inv.status == "overdue" and inv.days_overdue >= days
        ]

    def create(self, model: Invoice, lines: list[dict] | None = None) -> Invoice:
        pd = mp.parse_date(model.payment_date) if model.payment_date else None
        sale_d = mp.parse_date(model.sale_date) if model.sale_date else None
        dep_id = mp.parse_uuid(model.deposit_id) if model.deposit_id else None
        vr_id = mp.parse_uuid(model.visit_report_id) if model.visit_report_id else None
        row = orm.Invoice(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            deposit_id=dep_id,
            visit_report_id=vr_id,
            invoice_number=model.invoice_number,
            amount=float(model.amount),
            issue_date=mp.parse_date(model.issue_date),
            due_date=mp.parse_date(model.due_date),
            sale_date=sale_d,
            invoice_billing_type=model.billing_type,
            amount_ht=float(model.amount_ht) if model.amount_ht is not None else None,
            amount_vat=float(model.amount_vat) if model.amount_vat is not None else None,
            amount_ttc=float(model.amount_ttc) if model.amount_ttc is not None else None,
            status=model.status,
            payment_date=pd,
            reference_external=model.sage_reference,
            external_provider=model.external_provider,
            external_invoice_id=model.external_invoice_id,
            mock_provider_payload=model.mock_provider_payload,
            days_overdue=int(model.days_overdue or 0),
        )
        self._db.add(row)
        self._db.flush()
        if lines:
            for li in lines:
                self._db.add(
                    orm.InvoiceLine(
                        invoice_id=row.id,
                        product_id=mp.parse_uuid(li["product_id"]),
                        quantity=int(li["quantity"]),
                        unit_price=float(li["unit_price"]),
                        vat_rate=float(li["vat_rate"]),
                        is_free_unit=bool(li.get("is_free_unit", False)),
                        discount_percent=float(li.get("discount_percent", 0) or 0),
                        line_total_ht=(
                            float(li["line_total_ht"]) if li.get("line_total_ht") is not None else None
                        ),
                        reference_unit_price_ht=(
                            float(li["reference_unit_price_ht"])
                            if li.get("reference_unit_price_ht") is not None
                            else None
                        ),
                    )
                )
            self._db.flush()
        return mp.invoice_orm_to_domain(row)

    def update(self, id_: str, model: Invoice) -> Optional[Invoice]:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Invoice, iid)
        if not row:
            return None
        row.pharmacy_id = mp.parse_uuid(model.pharmacy_id)
        row.deposit_id = mp.parse_uuid(model.deposit_id) if model.deposit_id else None
        row.visit_report_id = mp.parse_uuid(model.visit_report_id) if model.visit_report_id else None
        row.invoice_number = model.invoice_number
        row.amount = float(model.amount)
        row.issue_date = mp.parse_date(model.issue_date)
        row.due_date = mp.parse_date(model.due_date)
        row.sale_date = mp.parse_date(model.sale_date) if model.sale_date else None
        row.invoice_billing_type = model.billing_type
        row.amount_ht = float(model.amount_ht) if model.amount_ht is not None else None
        row.amount_vat = float(model.amount_vat) if model.amount_vat is not None else None
        row.amount_ttc = float(model.amount_ttc) if model.amount_ttc is not None else None
        row.status = model.status
        row.payment_date = mp.parse_date(model.payment_date) if model.payment_date else None
        row.reference_external = model.sage_reference
        row.external_provider = model.external_provider
        row.external_invoice_id = model.external_invoice_id
        row.mock_provider_payload = model.mock_provider_payload
        row.days_overdue = int(model.days_overdue or 0)
        self._db.flush()
        return mp.invoice_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Invoice, iid)
        if not row:
            return False
        self._db.delete(row)
        return True
