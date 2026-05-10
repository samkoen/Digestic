from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.session_roles import require_admin_user_id, require_user_id
from app.dependencies import get_db
from app.services.pharmacy_advanced_filter_service import (
    create_filter,
    delete_filter,
    get_one,
    list_filters,
    update_filter,
)

router = APIRouter()


class PharmacyAdvancedFilterPayloadBody(BaseModel):
    combine: str = Field(default="and", max_length=8)
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class PharmacyAdvancedFilterCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    payload: PharmacyAdvancedFilterPayloadBody


class PharmacyAdvancedFilterUpdateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    payload: PharmacyAdvancedFilterPayloadBody


@router.get("")
def api_list(request: Request, db: Session = Depends(get_db)) -> Any:
    try:
        require_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        return list_filters(db)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{filter_id}")
def api_get(request: Request, filter_id: str, db: Session = Depends(get_db)) -> Any:
    try:
        require_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    row = get_one(db, filter_id)
    if row is None:
        return JSONResponse({"error": "Filtre non trouvé"}, status_code=404)
    return row


@router.post("")
def api_create(
    request: Request,
    body: PharmacyAdvancedFilterCreateBody,
    db: Session = Depends(get_db),
) -> Any:
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        return create_filter(
            db,
            {
                "name": body.name,
                "payload": body.payload.model_dump(),
            },
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/{filter_id}")
def api_put(
    request: Request,
    filter_id: str,
    body: PharmacyAdvancedFilterUpdateBody,
    db: Session = Depends(get_db),
) -> Any:
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        out = update_filter(
            db,
            filter_id,
            {
                "name": body.name,
                "payload": body.payload.model_dump(),
            },
        )
        if out is None:
            return JSONResponse({"error": "Filtre non trouvé"}, status_code=404)
        return out
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/{filter_id}")
def api_delete(
    request: Request, filter_id: str, db: Session = Depends(get_db)
) -> Any:
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    ok = delete_filter(db, filter_id)
    if not ok:
        return JSONResponse({"error": "Filtre non trouvé"}, status_code=404)
    return {"ok": True}
