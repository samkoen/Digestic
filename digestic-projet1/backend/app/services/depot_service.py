"""Logique métier des dépôts et transferts."""
from __future__ import annotations

from typing import Any, Optional

from app.repositories.depot_repository import DepotRepository


class DepotService:
    def __init__(self, repository: DepotRepository):
        self._repo = repository

    def list_depots(self) -> list[dict[str, Any]]:
        return self._repo.list_all()

    def get_depot(self, depot_id: str) -> Optional[dict[str, Any]]:
        return self._repo.get_dict_by_id(depot_id)

    def create_depot(self, data: dict[str, Any]) -> dict[str, Any]:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Le nom du dépôt est requis")
        raw_type = (data.get("depot_type") or "secondaire").strip().lower()
        if raw_type not in ("central", "secondaire"):
            raise ValueError("Type de dépôt invalide (central ou secondaire)")
        return self._repo.create(
            name=name,
            address_line=(data.get("address") or data.get("address_line") or None),
            city=(data.get("city") or None),
            postal_code=(data.get("postal_code") or None),
            country=(data.get("country") or "FR")[:2].upper(),
            depot_type=raw_type,
            quantity=int(data.get("quantity") or 0),
        )

    def update_depot(self, depot_id: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        u: dict[str, Any] = {}
        if "name" in data and data["name"] is not None:
            u["name"] = str(data["name"])
        if "address" in data or "address_line" in data:
            u["address_line"] = data.get("address_line") or data.get("address")
        if "city" in data:
            u["city"] = data.get("city")
        if "postal_code" in data:
            u["postal_code"] = data.get("postal_code")
        if "country" in data and data["country"] is not None:
            u["country"] = str(data["country"])[:2].upper()
        if "depot_type" in data and data["depot_type"] is not None:
            t = str(data["depot_type"]).strip().lower()
            if t not in ("central", "secondaire"):
                raise ValueError("Type de dépôt invalide")
            u["depot_type"] = t
        if "quantity" in data and data["quantity"] is not None:
            u["quantity"] = int(data["quantity"])
        if "is_active" in data and data["is_active"] is not None:
            u["is_active"] = bool(data["is_active"])
        if not u:
            return self._repo.get_dict_by_id(depot_id)
        return self._repo.update(depot_id, **u)

    def add_central_stock(self, depot_id: str, data: dict[str, Any]) -> dict[str, Any]:
        q = int(data.get("quantity") or 0)
        out = self._repo.add_central_stock(depot_id, q)
        if not out:
            return None
        return out

    def transfer(
        self,
        data: dict[str, Any],
        user_id: str | None,
    ) -> dict[str, Any]:
        return self._repo.transfer(
            from_warehouse_id=str(data.get("from_warehouse_id") or data.get("from_id") or ""),
            to_warehouse_id=str(data.get("to_warehouse_id") or data.get("to_id") or ""),
            quantity=int(data.get("quantity") or 0),
            user_id=user_id,
        )

    def list_transfers(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._repo.list_recent_transfers(limit=limit)
