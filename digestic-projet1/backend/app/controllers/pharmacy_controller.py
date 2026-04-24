from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.pharmacy_service import PharmacyService

router = APIRouter()


def get_pharmacy_service(db: Session = Depends(get_db)) -> PharmacyService:
    return PharmacyService(PharmacyRepository(db))


@router.get("")
def get_pharmacies(
    request: Request,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        user_role = request.session.get("user_role")
        user_id = request.session.get("user_id")
        if user_role == "commercial" and user_id:
            all_pharmacies = service.get_all_pharmacies()
            pharmacies = [p for p in all_pharmacies if p.commercial_id == user_id]
        else:
            pharmacies = service.get_all_pharmacies()
        return [pharmacy.to_dict() for pharmacy in pharmacies]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{pharmacy_id}")
def get_pharmacy(
    pharmacy_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.get_pharmacy_by_id(pharmacy_id)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_pharmacy(
    data: dict[str, Any],
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.create_pharmacy(data)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{pharmacy_id}")
def update_pharmacy(
    pharmacy_id: str,
    data: dict[str, Any],
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.update_pharmacy(pharmacy_id, data)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{pharmacy_id}")
def delete_pharmacy(
    pharmacy_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        success = service.delete_pharmacy(pharmacy_id)
        if not success:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return {"message": "Pharmacie supprimée avec succès"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
