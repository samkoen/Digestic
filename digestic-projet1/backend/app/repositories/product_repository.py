"""Produits : CRUD et résolution du produit par défaut pour la facturation."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.product import Product


def get_default_billing_product_row(db: Session) -> orm.Product | None:
    row = db.execute(
        select(orm.Product)
        .where(
            orm.Product.is_active.is_(True),
            orm.Product.is_default_for_billing.is_(True),
        )
        .order_by(orm.Product.name)
        .limit(1)
    ).scalar_one_or_none()
    if row:
        return row
    return db.execute(
        select(orm.Product)
        .where(orm.Product.is_active.is_(True))
        .order_by(orm.Product.name)
        .limit(1)
    ).scalar_one_or_none()


def get_default_billing_product_id(db: Session) -> uuid.UUID | None:
    p = get_default_billing_product_row(db)
    return p.id if p else None


def _norm_optional_str(v: str | None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


class ProductRepository:
    def __init__(self, db: Session):
        self._db = db

    def _clear_other_default_billing(self, keep_id: uuid.UUID | None) -> None:
        stmt = update(orm.Product).values(is_default_for_billing=False)
        if keep_id is not None:
            stmt = stmt.where(orm.Product.id != keep_id)
        self._db.execute(stmt)

    def find_all(self, *, active_only: bool = False) -> list[Product]:
        q = select(orm.Product).order_by(orm.Product.name)
        if active_only:
            q = q.where(orm.Product.is_active.is_(True))
        rows = self._db.execute(q).scalars().all()
        return [mp.product_orm_to_domain(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[Product]:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Product, pid)
        return mp.product_orm_to_domain(row) if row else None

    def create(self, model: Product) -> Product:
        if model.is_default_for_billing:
            self._clear_other_default_billing(keep_id=None)
        row = orm.Product(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            code=_norm_optional_str(model.code),
            ean=_norm_optional_str(getattr(model, "ean", None)),
            name=model.name.strip(),
            description=model.description,
            wholesale_unit_price=float(model.wholesale_unit_price),
            currency=(model.currency or "EUR")[:3].upper(),
            vat_rate=float(model.vat_rate),
            units_per_carton=int(model.units_per_carton),
            is_default_for_billing=bool(model.is_default_for_billing),
            is_active=bool(model.is_active),
        )
        self._db.add(row)
        self._db.flush()
        return mp.product_orm_to_domain(row)

    def update(self, id_: str, model: Product) -> Optional[Product]:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Product, pid)
        if not row:
            return None
        if model.is_default_for_billing:
            self._clear_other_default_billing(keep_id=row.id)
        row.code = _norm_optional_str(model.code)
        row.ean = _norm_optional_str(getattr(model, "ean", None))
        row.name = model.name.strip()
        row.description = model.description
        row.wholesale_unit_price = float(model.wholesale_unit_price)
        row.currency = (model.currency or "EUR")[:3].upper()
        row.vat_rate = float(model.vat_rate)
        row.units_per_carton = int(model.units_per_carton)
        row.is_default_for_billing = bool(model.is_default_for_billing)
        row.is_active = bool(model.is_active)
        self._db.flush()
        return mp.product_orm_to_domain(row)

    def soft_delete(self, id_: str) -> bool:
        try:
            pid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Product, pid)
        if not row:
            return False
        row.is_active = False
        if row.is_default_for_billing:
            row.is_default_for_billing = False
        self._db.flush()
        return True
