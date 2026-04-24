import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.invoice import Invoice


class InvoiceRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[Invoice]:
        rows = self._db.execute(select(orm.Invoice)).scalars().all()
        return [mp.invoice_orm_to_domain(r) for r in rows]

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

    def create(self, model: Invoice) -> Invoice:
        pd = mp.parse_date(model.payment_date) if model.payment_date else None
        row = orm.Invoice(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            invoice_number=model.invoice_number,
            amount=float(model.amount),
            issue_date=mp.parse_date(model.issue_date),
            due_date=mp.parse_date(model.due_date),
            status=model.status,
            payment_date=pd,
            reference_external=model.sage_reference,
            days_overdue=int(model.days_overdue or 0),
        )
        self._db.add(row)
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
        row.invoice_number = model.invoice_number
        row.amount = float(model.amount)
        row.issue_date = mp.parse_date(model.issue_date)
        row.due_date = mp.parse_date(model.due_date)
        row.status = model.status
        row.payment_date = mp.parse_date(model.payment_date) if model.payment_date else None
        row.reference_external = model.sage_reference
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
