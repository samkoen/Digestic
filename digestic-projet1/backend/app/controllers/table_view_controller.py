from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.session_roles import require_admin_user_id, require_user_id
from app.dependencies import get_db
from app.services import saved_list_filter_service, table_view_service

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


@router.get("/invoices")
def get_invoices_table_view(db: Session = Depends(get_db)) -> Any:
    try:
        return table_view_service.get_invoices_table_view(db)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/invoices")
def put_invoices_table_view(
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
        return table_view_service.set_invoices_table_view(
            db, body["visibleColumnKeys"], admin_id
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/delivery_notes")
def get_delivery_notes_table_view(db: Session = Depends(get_db)) -> Any:
    try:
        return table_view_service.get_delivery_notes_table_view(db)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/delivery_notes")
def put_delivery_notes_table_view(
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
        return table_view_service.set_delivery_notes_table_view(
            db, body["visibleColumnKeys"], admin_id
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{view_key}/saved-filters")
def list_saved_filters(
    request: Request,
    view_key: str,
    db: Session = Depends(get_db),
) -> Any:
    if view_key not in saved_list_filter_service.ALLOWED_VIEWS:
        return JSONResponse({"error": "Vue inconnue"}, status_code=404)
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        return saved_list_filter_service.list_for_user(db, uid, view_key)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{view_key}/saved-filters")
def create_saved_filter(
    request: Request,
    view_key: str,
    body: dict[str, Any] | None = Body(default=None),
    db: Session = Depends(get_db),
) -> Any:
    if view_key not in saved_list_filter_service.ALLOWED_VIEWS:
        return JSONResponse({"error": "Vue inconnue"}, status_code=404)
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        return saved_list_filter_service.create(db, uid, view_key, body)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/{view_key}/saved-filters/{filter_id}")
def delete_saved_filter(
    request: Request,
    view_key: str,
    filter_id: str,
    db: Session = Depends(get_db),
) -> Any:
    if view_key not in saved_list_filter_service.ALLOWED_VIEWS:
        return JSONResponse({"error": "Vue inconnue"}, status_code=404)
    try:
        uid = require_user_id(request)
    except HTTPException as e:
        return JSONResponse(
            {"error": str(e.detail)}, status_code=int(e.status_code)
        )
    try:
        ok = saved_list_filter_service.delete_for_user(db, uid, view_key, filter_id)
        if not ok:
            return JSONResponse({"error": "Filtre non trouvé"}, status_code=404)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
