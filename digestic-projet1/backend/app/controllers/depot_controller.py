"""API des dépôts (stocks) et transferts inter-dépôts."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.depot_repository import DepotRepository
from app.services.depot_service import DepotService

router = APIRouter()


def get_depot_service(db: Session = Depends(get_db)) -> DepotService:
    return DepotService(DepotRepository(db))


@router.get("")
def list_depots(service: DepotService = Depends(get_depot_service)):
    try:
        return service.list_depots()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/transfers")
def list_transfers(
    service: DepotService = Depends(get_depot_service),
    limit: int = Query(100, ge=1, le=500),
):
    try:
        return service.list_transfers(limit=limit)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{depot_id}")
def get_depot(
    depot_id: str,
    service: DepotService = Depends(get_depot_service),
):
    try:
        d = service.get_depot(depot_id)
        if not d:
            return JSONResponse({"error": "Dépôt non trouvé"}, status_code=404)
        return d
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_depot(
    data: dict[str, Any],
    service: DepotService = Depends(get_depot_service),
):
    try:
        return service.create_depot(data or {})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{depot_id}")
def update_depot(
    depot_id: str,
    data: dict[str, Any],
    service: DepotService = Depends(get_depot_service),
):
    try:
        d = service.update_depot(depot_id, data or {})
        if not d:
            return JSONResponse({"error": "Dépôt non trouvé"}, status_code=404)
        return d
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{depot_id}/add-stock")
def add_central_stock(
    depot_id: str,
    data: dict[str, Any],
    service: DepotService = Depends(get_depot_service),
):
    try:
        out = service.add_central_stock(depot_id, data or {})
        if not out:
            return JSONResponse({"error": "Dépôt non trouvé"}, status_code=404)
        return out
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/transfer", status_code=201)
def transfer_between_depots(
    data: dict[str, Any],
    request: Request,
    service: DepotService = Depends(get_depot_service),
):
    try:
        uid: Optional[str] = None
        if request.session:
            u = request.session.get("user_id")
            uid = str(u) if u else None
        return service.transfer(data or {}, user_id=uid)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
