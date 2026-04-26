from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.session_roles import require_admin_user_id, require_user_id
from app.dependencies import get_db
from app.services import pharmacy_saved_filter_service, table_view_service

router = APIRouter()


@router.get("/pharmacies")
def get_pharmacy_table_view(db: Session = Depends(get_db)) -> Any:
    try:
        return table_view_service.get_pharmacies_table_view(db)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/pharmacies")
def put_pharmacy_table_view(
    request: Request,
    body: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
) -> Any:
    if not body or not isinstance(body.get("visibleColumnKeys"), list):
        return JSONResponse(
            {"error": "visibleColumnKeys (liste) requis"},
            status_code=400,
        )
    try:
        admin_id = require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        return table_view_service.set_pharmacies_table_view(
            db, body["visibleColumnKeys"], admin_id
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/pharmacies/saved-filters")
def list_pharmacy_saved_filters(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        return pharmacy_saved_filter_service.list_for_user(db, uid)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/pharmacies/saved-filters")
def create_pharmacy_saved_filter(
    request: Request,
    body: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
) -> Any:
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        return pharmacy_saved_filter_service.create(db, uid, body)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/pharmacies/saved-filters/{filter_id}")
def delete_pharmacy_saved_filter(
    request: Request,
    filter_id: str,
    db: Session = Depends(get_db),
) -> Any:
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        ok = pharmacy_saved_filter_service.delete_for_user(db, uid, filter_id)
        if not ok:
            return JSONResponse({"error": "Filtre non trouvé"}, status_code=404)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
