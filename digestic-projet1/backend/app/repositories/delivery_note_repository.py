import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.domain.billing.delivery_note_number import new_digestic_bl_number
from app.domain.delivery_note_table_columns import DELIVERY_NOTE_SORT_KEYS
from app.models.delivery_note import DeliveryNote
from app.pagination import PageResult, normalize_page_input, offset_for_page


@dataclass(frozen=True)
class DeliveryNoteListRow:
    deposit: orm.Deposit
    pharmacy_name: str
    commercial_first_name: str
    commercial_last_name: str


def _parse_uuid_list(raw: list[str] | None) -> list[uuid.UUID]:
    if not raw:
        return []
    out: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for x in raw:
        try:
            u = mp.parse_uuid(str(x).strip())
        except ValueError:
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _delivery_note_order(sort: str, order: str, d, ph, u):
    desc_ = (order or "desc").lower() == "desc"
    skey = sort if sort in DELIVERY_NOTE_SORT_KEYS else "deliveryDate"

    def one(col):
        return col.desc() if desc_ else col.asc()

    if skey == "pharmacyName":
        return one(ph.name)
    if skey == "deliveryDate":
        return one(d.delivery_date)
    if skey == "bottlesCount":
        return one(d.bottles_count)
    if skey == "freeUnits":
        return one(d.free_units_quantity)
    if skey == "commercial":
        return (one(u.last_name), one(u.first_name))
    if skey == "status":
        return one(d.status)
    if skey == "isDepositSale":
        return one(d.is_deposit_sale)
    if skey == "sageReference":
        return one(d.reference_external)
    if skey == "blNumber":
        return one(d.bl_number)
    if skey == "depositId":
        return one(d.id)
    if skey == "emailSent":
        return one(d.email_sent)
    return one(d.delivery_date)


class DeliveryNoteRepository:
    """Persistance des bons (table `deposits`), API inchangée (DeliveryNote)."""

    def __init__(self, db: Session):
        self._db = db

    def _model_from_dict(self, data: dict) -> DeliveryNote:
        return DeliveryNote.from_dict(data)

    def search_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "deliveryDate",
        order: str = "desc",
        pharmacy_ids: list[str] | None = None,
        commercial_ids: list[str] | None = None,
        status: str | None = None,
        delivery_date_from: date | None = None,
        delivery_date_to: date | None = None,
        deposit_id: str | None = None,
        pharmacy_name: str | None = None,
        include_archived: bool = False,
        sage_reference: str | None = None,
        is_deposit_sale: bool | None = None,
        email_sent: str | None = None,
        restricted_to_commercial_id: str | None = None,
    ) -> PageResult[DeliveryNoteListRow]:
        """Liste paginée avec jointures pharmacie + commercial (tri SQL)."""
        p1, ps = normalize_page_input(page, page_size)
        off = offset_for_page(p1, ps)
        d, ph, u = orm.Deposit, orm.Pharmacy, orm.User

        base = (
            select(d, ph.name, u.first_name, u.last_name)
            .select_from(d)
            .join(ph, d.pharmacy_id == ph.id)
            .join(u, d.commercial_id == u.id)
        )
        conds: list = []
        if not include_archived:
            # BL facturés : bottles_count=0 mais statut fully_invoiced — ils doivent rester visibles.
            conds.append(or_(d.bottles_count > 0, d.status == "fully_invoiced"))

        pids = _parse_uuid_list(pharmacy_ids)
        if pids:
            conds.append(d.pharmacy_id.in_(pids))

        cids = _parse_uuid_list(commercial_ids)
        if cids:
            conds.append(d.commercial_id.in_(cids))

        if restricted_to_commercial_id and str(restricted_to_commercial_id).strip():
            try:
                conds.append(
                    d.commercial_id == mp.parse_uuid(str(restricted_to_commercial_id).strip())
                )
            except ValueError:
                conds.append(d.commercial_id == uuid.uuid4())

        if status and str(status).strip():
            conds.append(d.status == str(status).strip())

        if delivery_date_from is not None:
            conds.append(d.delivery_date >= delivery_date_from)
        if delivery_date_to is not None:
            conds.append(d.delivery_date <= delivery_date_to)

        if deposit_id and str(deposit_id).strip():
            try:
                conds.append(d.id == mp.parse_uuid(str(deposit_id).strip()))
            except ValueError:
                conds.append(d.id == uuid.uuid4())

        if pharmacy_name and str(pharmacy_name).strip():
            pat = f"%{str(pharmacy_name).strip()}%"
            conds.append(ph.name.ilike(pat))

        if sage_reference and str(sage_reference).strip():
            pat = f"%{str(sage_reference).strip()}%"
            conds.append(d.reference_external.ilike(pat))

        if is_deposit_sale is True or is_deposit_sale is False:
            conds.append(d.is_deposit_sale == is_deposit_sale)

        if email_sent is not None and str(email_sent).strip():
            es = str(email_sent).strip().lower()
            if es in ("yes", "oui", "1", "true"):
                conds.append(d.email_sent.is_(True))
            elif es in ("no", "non", "0", "false"):
                conds.append(d.email_sent.is_(False))

        where = and_(*conds) if conds else None
        if where is not None:
            base = base.where(where)

        count_q = (
            select(func.count())
            .select_from(d)
            .join(ph, d.pharmacy_id == ph.id)
            .join(u, d.commercial_id == u.id)
        )
        if where is not None:
            count_q = count_q.where(where)
        total = int(self._db.execute(count_q).scalar() or 0)

        ob = _delivery_note_order(sort, order, d, ph, u)
        page_q = base.order_by(*ob) if isinstance(ob, tuple) else base.order_by(ob)
        page_q = page_q.offset(off).limit(ps)
        raw_rows = self._db.execute(page_q).all()
        items: list[DeliveryNoteListRow] = []
        for row in raw_rows:
            dep, pname, fn, ln = row[0], row[1], row[2], row[3]
            items.append(
                DeliveryNoteListRow(
                    deposit=dep,
                    pharmacy_name=str(pname) if pname is not None else "",
                    commercial_first_name=str(fn or ""),
                    commercial_last_name=str(ln or ""),
                )
            )
        return PageResult(items=items, total=total, page=p1, page_size=ps)

    def find_all(self) -> list[DeliveryNote]:
        rows = self._db.execute(
            select(orm.Deposit).where(
                or_(
                    orm.Deposit.bottles_count > 0,
                    orm.Deposit.status == "fully_invoiced",
                )
            )
        ).scalars().all()
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
        q = q.where(
            or_(
                orm.Deposit.bottles_count > 0,
                orm.Deposit.status == "fully_invoiced",
            )
        )
        rows = self._db.execute(q).scalars().all()
        return [mp.deposit_orm_to_note(r) for r in rows]

    def find_by_pharmacy(self, pharmacy_id: str) -> list[DeliveryNote]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def find_by_commercial(self, commercial_id: str) -> list[DeliveryNote]:
        return self.find_by(commercial_id=commercial_id)

    def find_pending(self) -> list[DeliveryNote]:
        q = select(orm.Deposit).where(
            orm.Deposit.status == "pending",
            orm.Deposit.bottles_count > 0,
        )
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
            bl_number=(
                (model.bl_number or "").strip()
                or new_digestic_bl_number(for_date=ddel)
            ),
            email_sent=model.email_sent,
            email_sent_at=email_at,
            bottles_count=int(model.bottles_count or 0),
            free_units_quantity=int(getattr(model, "free_units_quantity", 0) or 0),
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
        bn = (getattr(model, "bl_number", None) or "").strip()
        if bn:
            row.bl_number = bn
        row.email_sent = model.email_sent
        row.bottles_count = int(model.bottles_count or 0)
        row.free_units_quantity = int(getattr(model, "free_units_quantity", 0) or 0)
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
