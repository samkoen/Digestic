import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.delivery_note import DeliveryNote


class DeliveryNoteRepository:
    """Persistance des bons (table `deposits`), API inchangée (DeliveryNote)."""

    def __init__(self, db: Session):
        self._db = db

    def _model_from_dict(self, data: dict) -> DeliveryNote:
        return DeliveryNote.from_dict(data)

    def find_all(self) -> list[DeliveryNote]:
        rows = self._db.execute(select(orm.Deposit)).scalars().all()
        return [mp.deposit_orm_to_note(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[DeliveryNote]:
        try:
            did = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Deposit, did)
        return mp.deposit_orm_to_note(row) if row else None

    def find_by(self, **kwargs) -> list[DeliveryNote]:
        q = select(orm.Deposit)
        for k, v in kwargs.items():
            if k in ("pharmacy_id", "commercial_id", "visit_report_id") and v is not None:
                v = mp.parse_uuid(v)
            attr = "reference_external" if k == "sage_reference" else k
            if not hasattr(orm.Deposit, attr):
                continue
            q = q.where(getattr(orm.Deposit, attr) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.deposit_orm_to_note(r) for r in rows]

    def find_by_pharmacy(self, pharmacy_id: str) -> list[DeliveryNote]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def find_by_commercial(self, commercial_id: str) -> list[DeliveryNote]:
        return self.find_by(commercial_id=commercial_id)

    def find_pending(self) -> list[DeliveryNote]:
        q = select(orm.Deposit).where(orm.Deposit.status == "pending")
        rows = self._db.execute(q).scalars().all()
        return [mp.deposit_orm_to_note(r) for r in rows]

    def _resolve_warehouse(self, pharmacy_id: str) -> uuid.UUID:
        ph = self._db.get(orm.Pharmacy, mp.parse_uuid(pharmacy_id))
        if not ph:
            raise ValueError("Pharmacie inconnue")
        return ph.warehouse_id

    def create(self, model: DeliveryNote) -> DeliveryNote:
        wh = self._resolve_warehouse(model.pharmacy_id)
        ddel = mp.parse_date(model.delivery_date)
        email_at = None
        if model.email_sent_at:
            try:
                email_at = datetime.fromisoformat(model.email_sent_at.replace("Z", "+00:00"))
            except ValueError:
                email_at = None
        row = orm.Deposit(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            visit_report_id=mp.parse_uuid(model.visit_report_id),
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            warehouse_id=wh,
            commercial_id=mp.parse_uuid(model.commercial_id),
            delivery_date=ddel,
            status=model.status or "pending",
            is_deposit_sale=bool(model.is_deposit_sale),
            reference_external=model.sage_reference,
            email_sent=model.email_sent,
            email_sent_at=email_at,
            bottles_count=int(model.bottles_count or 0),
        )
        self._db.add(row)
        self._db.flush()
        return mp.deposit_orm_to_note(row)

    def update(self, id_: str, model: DeliveryNote) -> Optional[DeliveryNote]:
        try:
            did = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Deposit, did)
        if not row:
            return None
        row.visit_report_id = mp.parse_uuid(model.visit_report_id)
        row.pharmacy_id = mp.parse_uuid(model.pharmacy_id)
        row.warehouse_id = self._resolve_warehouse(model.pharmacy_id)
        row.commercial_id = mp.parse_uuid(model.commercial_id)
        row.delivery_date = mp.parse_date(model.delivery_date)
        row.status = model.status
        row.is_deposit_sale = bool(model.is_deposit_sale)
        row.reference_external = model.sage_reference
        row.email_sent = model.email_sent
        row.bottles_count = int(model.bottles_count or 0)
        if model.email_sent_at:
            try:
                row.email_sent_at = datetime.fromisoformat(
                    model.email_sent_at.replace("Z", "+00:00")
                )
            except ValueError:
                pass
        self._db.flush()
        return mp.deposit_orm_to_note(row)

    def delete(self, id_: str) -> bool:
        try:
            did = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Deposit, did)
        if not row:
            return False
        self._db.delete(row)
        return True
