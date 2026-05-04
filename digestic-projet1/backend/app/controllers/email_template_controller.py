from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.session_roles import require_admin_user_id
from app.dependencies import get_db
from app.services.email_template_admin_service import EmailTemplateAdminService

router = APIRouter()


def get_email_template_admin_service(db: Session = Depends(get_db)) -> EmailTemplateAdminService:
    return EmailTemplateAdminService(db)


class EmailTemplateUpsertBody(BaseModel):
    subject_template: str = Field(..., min_length=1, max_length=2000)
    body_html_template: str = Field(..., min_length=1, max_length=500_000)


class EmailTemplateCreateBody(BaseModel):
    template_key: str = Field(..., min_length=2, max_length=64)
    subject_template: str = Field(..., min_length=1, max_length=2000)
    body_html_template: str = Field(..., min_length=1, max_length=500_000)


@router.get("")
def list_email_templates(
    request: Request,
    service: EmailTemplateAdminService = Depends(get_email_template_admin_service),
) -> Any:
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        return service.list_all()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/catalog")
def list_catalog_entries(
    request: Request,
    service: EmailTemplateAdminService = Depends(get_email_template_admin_service),
) -> Any:
    """Types documentés (variables disponibles par type d’e-mail)."""
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    return service.catalog_only()


@router.get("/{template_key}")
def get_email_template(
    request: Request,
    template_key: str,
    service: EmailTemplateAdminService = Depends(get_email_template_admin_service),
) -> Any:
    try:
        require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    row = service.get_one(template_key)
    if row is None:
        return JSONResponse({"error": "Modèle non trouvé"}, status_code=404)
    return row


@router.put("/{template_key}")
def put_email_template(
    request: Request,
    template_key: str,
    body: EmailTemplateUpsertBody,
    service: EmailTemplateAdminService = Depends(get_email_template_admin_service),
    db: Session = Depends(get_db),
) -> Any:
    try:
        admin_id = require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        updated = service.update_existing(
            template_key=template_key,
            subject_template=body.subject_template,
            body_html_template=body.body_html_template,
            admin_user_id=admin_id,
        )
        if updated is None:
            return JSONResponse({"error": "Modèle non trouvé"}, status_code=404)
        db.commit()
        return updated
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        db.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def post_email_template(
    request: Request,
    body: EmailTemplateCreateBody,
    service: EmailTemplateAdminService = Depends(get_email_template_admin_service),
    db: Session = Depends(get_db),
) -> Any:
    try:
        admin_id = require_admin_user_id(request)
    except HTTPException as e:
        return JSONResponse({"error": str(e.detail)}, status_code=int(e.status_code))
    try:
        created = service.create_custom(
            template_key=body.template_key,
            subject_template=body.subject_template,
            body_html_template=body.body_html_template,
            admin_user_id=admin_id,
        )
        db.commit()
        return created
    except ValueError as e:
        db.rollback()
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        db.rollback()
        return JSONResponse({"error": str(e)}, status_code=500)
