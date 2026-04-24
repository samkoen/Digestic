import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.db.bootstrap import get_or_create_default_warehouse_id
from app.models.pharmacy import Pharmacy


class PharmacyRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[Pharmacy]:
        rows = self._db.execute(select(orm.Pharmacy)).scalars().all()
        return [mp.pharm_orm_to_domain(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[Pharmacy]:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Pharmacy, pid)
        return mp.pharm_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[Pharmacy]:
        q = select(orm.Pharmacy)
        for k, v in kwargs.items():
            q = q.where(getattr(orm.Pharmacy, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.pharm_orm_to_domain(r) for r in rows]

    def _prepare_new(self, data: dict) -> dict:
        d = dict(data)
        if "address_line" not in d and "address" in d:
            d["address_line"] = d["address"]
        d.setdefault("country", "FR")
        d["email"] = (d.get("email") or d.get("pharmacist_email") or "").strip() or "inconnu@example.com"
        d["phone"] = (d.get("phone") or d.get("pharmacist_phone") or "").strip() or "0000000000"
        d["owner_name"] = d.get("owner_name") or d.get("pharmacist_name")
        d["owner_email"] = d.get("owner_email") or d.get("pharmacist_email")
        d["owner_phone"] = d.get("owner_phone") or d.get("pharmacist_phone")
        if not d.get("warehouse_id"):
            d["warehouse_id"] = str(get_or_create_default_warehouse_id(self._db))
        if not d.get("commercial_id"):
            raise ValueError("commercial_id est requis")
        d["payment_mode"] = mp.normalize_payment_mode_to_db(d.get("payment_mode"))
        if d.get("has_rib") is None:
            d["has_rib"] = bool(d.get("rib"))
        if d.get("pharmacy_status") is None and d.get("status") is None and "active" in d:
            a = d.get("active")
            d["pharmacy_status"] = "desactive" if a is False else "actif"
        raw = d.get("pharmacy_status") or d.get("status") or "actif"
        if raw is None or (isinstance(raw, str) and not str(raw).strip()):
            raw = "actif"
        raw = str(raw).strip().lower()[:32] or "actif"
        d["pharmacy_status"] = raw
        d.pop("status", None)
        d.pop("active", None)
        return d

    def create(self, model: Pharmacy) -> Pharmacy:
        d = self._prepare_new(model.to_dict())
        row = orm.Pharmacy(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            name=d["name"],
            address_line=d["address_line"],
            city=d["city"],
            postal_code=d["postal_code"],
            country=d["country"],
            phone=d["phone"],
            email=d["email"],
            email_secondary=d.get("email_secondary"),
            owner_name=d.get("owner_name"),
            owner_phone=d.get("owner_phone"),
            owner_email=d.get("owner_email"),
            warehouse_id=mp.parse_uuid(d["warehouse_id"]),
            commercial_id=mp.parse_uuid(d["commercial_id"]),
            has_rib=bool(d.get("has_rib", False)),
            rib=d.get("rib"),
            payment_mode=d["payment_mode"],
            gocardless_customer_id=d.get("gocardless_customer_id"),
            gocardless_mandate_id=d.get("gocardless_mandate_id"),
            pharmacy_status=d["pharmacy_status"],
            last_visit_at=None,
            next_visit_date=(
                mp.parse_date(d["next_visit_date"])
                if d.get("next_visit_date") not in (None, "")
                else None
            ),
            photo_url=d.get("photo_url"),
            latitude=d.get("latitude"),
            longitude=d.get("longitude"),
        )
        self._db.add(row)
        self._db.flush()
        return mp.pharm_orm_to_domain(row)

    def update(self, id_: str, model: Pharmacy) -> Optional[Pharmacy]:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Pharmacy, pid)
        if not row:
            return None
        d = self._prepare_new({**mp.pharm_orm_to_domain(row).to_dict(), **model.to_dict()})
        row.name = d["name"]
        row.address_line = d["address_line"]
        row.city = d["city"]
        row.postal_code = d["postal_code"]
        row.country = d["country"]
        row.phone = d["phone"]
        row.email = d["email"]
        row.email_secondary = d.get("email_secondary")
        row.owner_name = d.get("owner_name")
        row.owner_phone = d.get("owner_phone")
        row.owner_email = d.get("owner_email")
        row.warehouse_id = mp.parse_uuid(d["warehouse_id"])
        row.commercial_id = mp.parse_uuid(d["commercial_id"])
        row.has_rib = bool(d.get("has_rib", False))
        row.rib = d.get("rib")
        row.payment_mode = mp.normalize_payment_mode_to_db(d.get("payment_mode"))
        row.pharmacy_status = d["pharmacy_status"]
        row.next_visit_date = (
            mp.parse_date(d["next_visit_date"])
            if d.get("next_visit_date") not in (None, "")
            else None
        )
        row.photo_url = d.get("photo_url")
        row.latitude = d.get("latitude")
        row.longitude = d.get("longitude")
        self._db.flush()
        return mp.pharm_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Pharmacy, pid)
        if not row:
            return False
        self._db.delete(row)
        return True
