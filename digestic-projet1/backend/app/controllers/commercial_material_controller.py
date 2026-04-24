import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.commercial_material_repository import CommercialMaterialRepository

router = APIRouter()


def get_commercial_material_repository(
    db: Session = Depends(get_db),
) -> CommercialMaterialRepository:
    return CommercialMaterialRepository(db)


@router.get("")
def get_commercial_materials(
    active_only: bool = False,
    repo: CommercialMaterialRepository = Depends(get_commercial_material_repository),
):
    try:
        if active_only:
            materials = repo.find_active()
        else:
            materials = repo.find_all()
        return [material.to_dict() for material in materials]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{material_id}")
def get_commercial_material(
    material_id: str,
    repo: CommercialMaterialRepository = Depends(get_commercial_material_repository),
):
    try:
        material = repo.find_by_id(material_id)
        if not material:
            return JSONResponse(
                {"error": "Support commercial non trouvé"},
                status_code=404,
            )
        return material.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_commercial_material(
    data: dict[str, Any],
    repo: CommercialMaterialRepository = Depends(get_commercial_material_repository),
):
    try:
        data = dict(data)
        data["id"] = str(uuid.uuid4())
        material = repo._model_from_dict(data)
        material = repo.create(material)
        return material.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{material_id}")
def update_commercial_material(
    material_id: str,
    data: dict[str, Any],
    repo: CommercialMaterialRepository = Depends(get_commercial_material_repository),
):
    try:
        existing = repo.find_by_id(material_id)
        if not existing:
            return JSONResponse(
                {"error": "Support commercial non trouvé"},
                status_code=404,
            )
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.now().isoformat()
        material = repo.update(material_id, existing)
        return material.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
