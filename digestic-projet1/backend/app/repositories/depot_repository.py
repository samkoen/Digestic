"""Accès base pour les dépôts (warehouses) et transferts."""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp


def _wh_to_dict(w: orm.Warehouse) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "name": w.name,
        "address": w.address_line,
        "city": w.city,
        "postal_code": w.postal_code,
        "country": w.country,
        "depot_type": w.depot_type,
        "quantity": w.quantity,
        "is_active": w.is_active,
    }


def _transfer_to_dict(t: orm.DepotTransfer) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "from_warehouse_id": str(t.from_warehouse_id),
        "to_warehouse_id": str(t.to_warehouse_id),
        "quantity": t.quantity,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "created_by_user_id": (str(t.created_by_user_id) if t.created_by_user_id else None),
    }


class DepotRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self) -> list[dict[str, Any]]:
        rows = self._db.execute(
            select(orm.Warehouse).order_by(orm.Warehouse.name)
        ).scalars().all()
        return [_wh_to_dict(r) for r in rows]

    def get_by_id(self, id_: str) -> Optional[orm.Warehouse]:
        try:
            wid = mp.parse_uuid(id_)
        except ValueError:
            return None
        return self._db.get(orm.Warehouse, wid)

    def get_dict_by_id(self, id_: str) -> Optional[dict[str, Any]]:
        w = self.get_by_id(id_)
        return _wh_to_dict(w) if w else None

    def create(
        self,
        *,
        name: str,
        address_line: str | None,
        city: str | None,
        postal_code: str | None,
        country: str,
        depot_type: str,
        quantity: int = 0,
    ) -> dict[str, Any]:
        row = orm.Warehouse(
            name=name.strip(),
            address_line=address_line,
            city=city,
            postal_code=postal_code,
            country=country,
            depot_type=depot_type,
            quantity=max(0, int(quantity)),
            is_active=True,
        )
        self._db.add(row)
        self._db.flush()
        return _wh_to_dict(row)

    def update(
        self,
        id_: str,
        *,
        name: str | None = None,
        address_line: str | None = None,
        city: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        depot_type: str | None = None,
        quantity: int | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        row = self.get_by_id(id_)
        if not row:
            return None
        if name is not None:
            row.name = name.strip()
        if address_line is not None:
            row.address_line = address_line
        if city is not None:
            row.city = city
        if postal_code is not None:
            row.postal_code = postal_code
        if country is not None:
            row.country = country
        if depot_type is not None:
            row.depot_type = depot_type
        if quantity is not None:
            row.quantity = max(0, int(quantity))
        if is_active is not None:
            row.is_active = is_active
        self._db.flush()
        return _wh_to_dict(row)

    def add_central_stock(self, id_: str, amount: int) -> dict[str, Any] | None:
        if amount <= 0:
            raise ValueError("La quantité à ajouter doit être positive")
        row = self.get_by_id(id_)
        if not row:
            return None
        if row.depot_type != "central":
            raise ValueError("L'ajout de stock n'est autorisé que sur un dépôt central")
        row.quantity += int(amount)
        self._db.flush()
        return _wh_to_dict(row)

    def transfer(
        self,
        *,
        from_warehouse_id: str,
        to_warehouse_id: str,
        quantity: int,
        user_id: str | None,
    ) -> dict[str, Any]:
        if quantity <= 0:
            raise ValueError("La quantité transférée doit être positive")
        wid_from = mp.parse_uuid(from_warehouse_id)
        wid_to = mp.parse_uuid(to_warehouse_id)
        if wid_from == wid_to:
            raise ValueError("Les dépôts source et destination doivent être distincts")
        a = self._db.get(orm.Warehouse, wid_from)
        b = self._db.get(orm.Warehouse, wid_to)
        if not a or not b:
            raise ValueError("Dépôt introuvable")
        if a.quantity < quantity:
            raise ValueError("Stock insuffisant sur le dépôt source")
        uid = None
        if user_id:
            try:
                uid = mp.parse_uuid(user_id)
            except ValueError:
                uid = None
        a.quantity -= int(quantity)
        b.quantity += int(quantity)
        log = orm.DepotTransfer(
            from_warehouse_id=wid_from,
            to_warehouse_id=wid_to,
            quantity=int(quantity),
            created_by_user_id=uid,
        )
        self._db.add(log)
        self._db.flush()
        return {
            "transfer": _transfer_to_dict(log),
            "from_warehouse": _wh_to_dict(a),
            "to_warehouse": _wh_to_dict(b),
        }

    def list_recent_transfers(self, limit: int = 100) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 500))
        rows = self._db.execute(
            select(orm.DepotTransfer).order_by(desc(orm.DepotTransfer.created_at)).limit(lim)
        ).scalars().all()
        return [_transfer_to_dict(t) for t in rows]
