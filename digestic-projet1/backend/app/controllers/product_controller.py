"""API CRUD produits (catalogue / facturation)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.product_repository import ProductRepository
from app.services.product_service import ProductService

router = APIRouter()


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(ProductRepository(db))


@router.get("")
def list_products(
    active_only: bool = Query(False, description="Limiter aux produits actifs"),
    service: ProductService = Depends(get_product_service),
):
    try:
        return [p.to_dict() for p in service.list_products(active_only=active_only)]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{product_id}")
def get_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):
    try:
        p = service.get_product(product_id)
        if not p:
            return JSONResponse({"error": "Produit non trouvé"}, status_code=404)
        return p.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_product(
    data: dict[str, Any],
    service: ProductService = Depends(get_product_service),
):
    try:
        p = service.create_product(data or {})
        return p.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{product_id}")
def update_product(
    product_id: str,
    data: dict[str, Any],
    service: ProductService = Depends(get_product_service),
):
    try:
        p = service.update_product(product_id, data or {})
        if not p:
            return JSONResponse({"error": "Produit non trouvé"}, status_code=404)
        return p.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{product_id}", status_code=200)
def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
):
    """Désactivation logique (conserve l'historique factures / stocks)."""
    try:
        if not service.deactivate_product(product_id):
            return JSONResponse({"error": "Produit non trouvé"}, status_code=404)
        return {"message": "Produit désactivé", "id": product_id}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
