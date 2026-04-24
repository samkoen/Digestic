from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.visit_report_repository import VisitReportRepository
from app.repositories.visit_repository import VisitRepository
from app.services.visit_report_service import VisitReportService

router = APIRouter()


def get_visit_report_service(db: Session = Depends(get_db)) -> VisitReportService:
    return VisitReportService(
        VisitReportRepository(db),
        DeliveryNoteRepository(db),
        VisitRepository(db),
        PharmacyRepository(db),
    )


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
