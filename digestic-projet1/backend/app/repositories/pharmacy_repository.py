import uuid
from dataclasses import dataclass
from datetime import date
from collections.abc import Sequence
from typing import Optional

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

import app.db.models as orm
from app.db import mappers as mp
from app.db.bootstrap import get_or_create_default_warehouse_id
from app.domain.pharmacy_table_columns import PHARMACY_SORT_KEYS
from app.models.pharmacy import Pharmacy
from app.pagination import offset_for_page, PageResult, normalize_page_input
from app.repositories.pharmacy_list_filters_extra import apply_extra_pharmacy_filters
from app.repositories.pharmacy_list_ordering import order_pharmacy_list


@dataclass(frozen=True)
class _PharmacyListRow:
    """Une ligne de liste (domaine + nom affichable du commercial)."""

    pharmacy: Pharmacy
    commercial_name: str


def _ilike_pattern(q: str) -> str:
    t = (q or "").strip()
    for ch in ("\\", "%", "_"):
        t = t.replace(ch, "\\" + ch)
    return f"%{t}%" if t else "%"


def _parse_uuid_list(raw: str | Sequence[str] | None) -> list[uuid.UUID]:
    if raw is None:
        return []
    if isinstance(raw, str):
        s = raw.strip()
        seq: Sequence[str] = [s] if s else []
    else:
        seq = raw
    out: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    for x in seq:
        try:
            u = mp.parse_uuid(str(x).strip())
        except ValueError:
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


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
        row = self._db.execute(
            select(orm.Pharmacy)
            .options(joinedload(orm.Pharmacy.warehouse))
            .where(orm.Pharmacy.id == pid)
        ).unique().scalar_one_or_none()
        return mp.pharm_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[Pharmacy]:
        q = select(orm.Pharmacy)
        for k, v in kwargs.items():
            q = q.where(getattr(orm.Pharmacy, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.pharm_orm_to_domain(r) for r in rows]

    def distinct_cities_sorted(self) -> list[str]:
        q = (
            select(orm.Pharmacy.city)
            .where(
                orm.Pharmacy.city.isnot(None),
                orm.Pharmacy.city != "",
            )
            .distinct()
            .order_by(orm.Pharmacy.city.asc())
        )
        rows = self._db.execute(q).scalars().all()
        return [str(r).strip() for r in rows if r and str(r).strip()]

    def search_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "name",
        order: str = "asc",
        name: Optional[str] = None,
        address: Optional[str] = None,
        commercial_id: str | Sequence[str] | None = None,
        last_visit: Optional[str] = None,
        next_visit: Optional[str] = None,
        pharmacy_status: Optional[str] = None,
        city: str | Sequence[str] | None = None,
        postal_code: str | Sequence[str] | None = None,
        country: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        owner_name: Optional[str] = None,
        payment_mode: str | Sequence[str] | None = None,
        created: Optional[str] = None,
        rib: Optional[str] = None,
        depot: Optional[str] = None,
        warehouse_id: str | Sequence[str] | None = None,
        restricted_to_commercial_id: Optional[str] = None,
    ) -> PageResult[_PharmacyListRow]:
        """Liste paginée : filtres + tri + jointure commercial, le tout côté SQL."""
        p, ps = normalize_page_input(page, page_size)
        sort_key = sort if sort in PHARMACY_SORT_KEYS else "name"
        asc = (str(order or "asc").lower() != "desc")

        p_tbl = orm.Pharmacy
        u = orm.User
        w_tbl = orm.Warehouse
        j = p_tbl.commercial_id == u.id
        j_w = p_tbl.warehouse_id == w_tbl.id
        conds: list = []

        if restricted_to_commercial_id:
            try:
                rid = mp.parse_uuid(restricted_to_commercial_id)
            except ValueError:
                return PageResult(items=[], total=0, page=p, page_size=ps)
            conds.append(p_tbl.commercial_id == rid)
        else:
            c_uuids = _parse_uuid_list(commercial_id)
            if c_uuids:
                conds.append(p_tbl.commercial_id.in_(c_uuids))
        if name and (name or "").strip():
            pat = _ilike_pattern(name)
            conds.append(p_tbl.name.ilike(pat, escape="\\"))
        if address and (address or "").strip():
            pat = _ilike_pattern(address)
            line = func.concat(
                p_tbl.address_line, " ", p_tbl.postal_code, " ", p_tbl.city
            )
            conds.append(line.ilike(pat, escape="\\"))
        if last_visit and (last_visit or "").strip():
            pat = _ilike_pattern(last_visit)
            conds.append(
                and_(
                    p_tbl.last_visit_at.isnot(None),
                    or_(
                        func.to_char(
                            p_tbl.last_visit_at, "DD/MM/YYYY"
                        ).ilike(pat, escape="\\"),
                        func.to_char(
                            p_tbl.last_visit_at, "YYYY-MM-DD"
                        ).ilike(pat, escape="\\"),
                        cast(p_tbl.last_visit_at, String).ilike(
                            pat, escape="\\"
                        ),
                    ),
                )
            )
        if next_visit and (next_visit or "").strip():
            try:
                nd = date.fromisoformat(str(next_visit)[:10])
                conds.append(p_tbl.next_visit_date == nd)
            except ValueError:
                pass
        if pharmacy_status and (pharmacy_status or "").strip():
            conds.append(
                p_tbl.pharmacy_status
                == str(pharmacy_status).strip().lower()[:32]
            )
        if rib and str(rib).strip():
            v = str(rib).strip().lower()
            if v in ("yes", "oui", "true", "1"):
                conds.append(p_tbl.has_rib.is_(True))
            elif v in ("no", "non", "false", "0"):
                conds.append(p_tbl.has_rib.is_(False))
        depot_name_filter = depot
        w_uuids = _parse_uuid_list(warehouse_id)
        if w_uuids:
            conds.append(p_tbl.warehouse_id.in_(w_uuids))
            depot_name_filter = None
        apply_extra_pharmacy_filters(
            conds,
            p_tbl,
            city=city,
            postal_code=postal_code,
            country=country,
            email=email,
            phone=phone,
            owner_name=owner_name,
            payment_mode=payment_mode,
            created=created,
            depot=depot_name_filter,
            warehouse=w_tbl,
        )

        def _base_count():
            c = (
                select(func.count(p_tbl.id))
                .select_from(p_tbl)
                .join(u, j)
                .join(w_tbl, j_w)
            )
            if conds:
                c = c.where(and_(*conds))
            return c

        def _base_select():
            s = select(p_tbl, u, w_tbl).select_from(p_tbl).join(u, j).join(w_tbl, j_w)
            if conds:
                s = s.where(and_(*conds))
            return s

        def _order(s):
            return order_pharmacy_list(s, sort_key, asc, p_tbl, u, w_tbl)

        total = int(self._db.scalar(_base_count()) or 0)
        if total == 0:
            return PageResult(items=[], total=0, page=p, page_size=ps)

        stmt = _order(_base_select())
        off = offset_for_page(p, ps)
        stmt = stmt.offset(off).limit(ps)
        rows = self._db.execute(stmt).all()
        out: list[_PharmacyListRow] = []
        for rowp, rowu, roww in rows:
            dom = mp.pharm_orm_to_domain(rowp, roww)
            cname = f"{rowu.first_name} {rowu.last_name}".strip()
            out.append(
                _PharmacyListRow(
                    pharmacy=dom,
                    commercial_name=cname,
                )
            )
        return PageResult(
            items=out,
            total=total,
            page=p,
            page_size=ps,
        )

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
        from app.core.payment_modes import is_prélèvement_sepa

        if is_prélèvement_sepa(d["payment_mode"]) and not (str(d.get("rib") or "").strip()):
            raise ValueError(
                "Le RIB est obligatoire lorsque le mode de paiement est un prélèvement SEPA."
            )
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
        return self.find_by_id(id_)

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
