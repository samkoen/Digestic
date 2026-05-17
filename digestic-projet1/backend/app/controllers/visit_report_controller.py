import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.pharmacy_comment_repository import PharmacyCommentRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.visit_report_repository import VisitReportRepository
from app.repositories.visit_repository import VisitRepository
from app.services.visit_report_service import VisitReportService

router = APIRouter()

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
VISIT_REPORT_MEDIA_DIR = BACKEND_DIR / "uploads" / "visit_reports"
MEDIA_MAX_BYTES = 50 * 1024 * 1024
MEDIA_ALLOWED_EXT = {
    ".webm",
    ".mp3",
    ".m4a",
    ".wav",
    ".ogg",
    ".opus",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".mov",
    ".m4v",
}


def get_visit_report_service(db: Session = Depends(get_db)) -> VisitReportService:
    return VisitReportService(
        db,
        VisitReportRepository(db),
        VisitRepository(db),
        PharmacyRepository(db),
        PharmacyCommentRepository(db),
    )


class LastDepositsByPharmacyBody(BaseModel):
    pharmacy_ids: list[str] = Field(default_factory=list)

    @field_validator("pharmacy_ids")
    @classmethod
    def cap_pharmacies(cls, v: list[str]) -> list[str]:
        if len(v) > 1500:
            raise ValueError("Au plus 1500 pharmacies par requête.")
        return v


@router.get("")
def get_visit_reports(
    commercial_id: str | None = None,
    pharmacy_id: str | None = None,
    service: VisitReportService = Depends(get_visit_report_service),
):
    try:
        if commercial_id:
            reports = service.get_reports_by_commercial(commercial_id)
        elif pharmacy_id:
            reports = service.get_reports_by_pharmacy(pharmacy_id)
        else:
            reports = service.get_all_reports()
        return [report.to_dict() for report in reports]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/last-deposits-by-pharmacy")
def post_last_deposits_by_pharmacy_for_planning(
    body: LastDepositsByPharmacyBody,
    service: VisitReportService = Depends(get_visit_report_service),
):
    """Pour la grille Planning : dernier rapport avec dépôt par pharmacie (liste bornée)."""
    try:
        items = service.get_last_deposits_for_planning(body.pharmacy_ids)
        return {"items": items}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/upload-media")
async def upload_visit_report_media(
    file: UploadFile = File(...),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in MEDIA_ALLOWED_EXT:
        raise HTTPException(
            status_code=400, detail="Type de fichier non autorisé pour la pièce jointe"
        )
    VISIT_REPORT_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    path = VISIT_REPORT_MEDIA_DIR / name
    data = await file.read()
    if len(data) > MEDIA_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 50 Mo)")
    path.write_bytes(data)
    return {"url": f"/uploads/visit_reports/{name}"}


@router.post("/sync", status_code=200)
def sync_visit_reports(
    service: VisitReportService = Depends(get_visit_report_service),
):
    try:
        count = service.sync_reports()
        return {"message": f"{count} rapports synchronisés", "count": count}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{report_id}")
def get_visit_report(
    report_id: str,
    service: VisitReportService = Depends(get_visit_report_service),
):
    try:
        report = service.get_report_by_id(report_id)
        if not report:
            return JSONResponse({"error": "Rapport non trouvé"}, status_code=404)
        return report.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_visit_report(
    data: dict[str, Any],
    service: VisitReportService = Depends(get_visit_report_service),
):
    try:
        report = service.create_report(data)
        return report.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{report_id}")
def update_visit_report(
    report_id: str,
    data: dict[str, Any],
    service: VisitReportService = Depends(get_visit_report_service),
):
    try:
        report = service.update_report(report_id, data)
        if not report:
            return JSONResponse({"error": "Rapport non trouvé"}, status_code=404)
        return report.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
