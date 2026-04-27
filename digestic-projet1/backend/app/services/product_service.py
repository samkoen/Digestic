"""Règles métier produits."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from app.models.product import Product
from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, repo: ProductRepository):
        self._repo = repo

    def list_products(self, *, active_only: bool = False) -> list[Product]:
        return self._repo.find_all(active_only=active_only)

    def get_product(self, product_id: str) -> Optional[Product]:
        return self._repo.find_by_id(product_id)

    def create_product(self, data: dict[str, Any]) -> Product:
        payload = self._validated_payload(dict(data or {}), for_create=True)
        payload["id"] = str(uuid.uuid4())
        return self._repo.create(Product.from_dict(payload))

    def update_product(self, product_id: str, data: dict[str, Any]) -> Optional[Product]:
        existing = self._repo.find_by_id(product_id)
        if not existing:
            return None
        merged = existing.to_dict()
        merged.update({k: v for k, v in (data or {}).items() if k in merged and k != "id"})
        payload = self._validated_payload(merged, for_create=False)
        payload["id"] = existing.id
        return self._repo.update(product_id, Product.from_dict(payload))

    def deactivate_product(self, product_id: str) -> bool:
        return self._repo.soft_delete(product_id)

    def _validated_payload(self, data: dict[str, Any], *, for_create: bool) -> dict[str, Any]:
        name = (data.get("name") or "").strip()
        if for_create and not name:
            raise ValueError("Le nom du produit est obligatoire")
        if not for_create and "name" in data:
            if not name:
                raise ValueError("Le nom du produit est obligatoire")

        if for_create:
            for req in ("wholesale_unit_price", "vat_rate", "units_per_carton"):
                if data.get(req) is None:
                    raise ValueError(f"Champ requis pour la création : {req}")

        out = dict(data)
        if "name" in out:
            out["name"] = name

        if "wholesale_unit_price" in out:
            p = float(out["wholesale_unit_price"])
            if p < 0:
                raise ValueError("Le prix unitaire HT ne peut pas être négatif")
            out["wholesale_unit_price"] = p

        if "vat_rate" in out:
            v = float(out["vat_rate"])
            if v < 0 or v > 100:
                raise ValueError("Le taux de TVA doit être compris entre 0 et 100")
            out["vat_rate"] = v

        if "units_per_carton" in out:
            u = int(out["units_per_carton"])
            if u < 1:
                raise ValueError("units_per_carton doit être au moins 1")
            out["units_per_carton"] = u

        if "currency" in out and out["currency"] is not None:
            out["currency"] = str(out["currency"]).strip().upper()[:3]
            if len(out["currency"]) != 3:
                raise ValueError("La devise doit être un code ISO sur 3 lettres")

        for key in ("is_active", "is_default_for_billing"):
            if key in out and out[key] is not None:
                out[key] = bool(out[key])

        return out
