from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.visit_repository import VisitRepository
from app.services.visit_service import VisitService

router = APIRouter()


def get_visit_service(db: Session = Depends(get_db)) -> VisitService:
    return VisitService(VisitRepository(db))


@router.get("")
def get_visits(
    commercial_id: str | None = None,
    pharmacy_id: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    service: VisitService = Depends(get_visit_service),
):
    try:
        if commercial_id:
            visits = service.get_visits_by_commercial(commercial_id)
        elif pharmacy_id:
            visits = service.get_visits_by_pharmacy(pharmacy_id)
        else:
            visits = service.get_all_visits()
        if status:
            visits = [v for v in visits if v.status == status]
        if start_date or end_date:
            filtered_visits = []
            for visit in visits:
                if not visit.scheduled_date:
                    continue
                visit_date = datetime.fromisoformat(
                    visit.scheduled_date.replace("Z", "+00:00")
                )
                if start_date:
                    start = datetime.fromisoformat(
                        start_date.replace("Z", "+00:00")
                    )
                    if visit_date < start:
                        continue
                if end_date:
                    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    if visit_date > end:
                        continue
                filtered_visits.append(visit)
            visits = filtered_visits
        return [visit.to_dict() for visit in visits]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{visit_id}")
def get_visit(
    visit_id: str,
    service: VisitService = Depends(get_visit_service),
):
    try:
        visit = service.get_visit_by_id(visit_id)
        if not visit:
            return JSONResponse({"error": "Visite non trouvée"}, status_code=404)
        return visit.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_visit(
    data: dict[str, Any],
    service: VisitService = Depends(get_visit_service),
):
    try:
        visit = service.create_visit(data)
        return visit.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{visit_id}")
def update_visit(
    visit_id: str,
    data: dict[str, Any],
    service: VisitService = Depends(get_visit_service),
):
    try:
        visit = service.update_visit(visit_id, data)
        if not visit:
            return JSONResponse({"error": "Visite non trouvée"}, status_code=404)
        return visit.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{visit_id}")
def delete_visit(
    visit_id: str,
    service: VisitService = Depends(get_visit_service),
):
    try:
        success = service.delete_visit(visit_id)
        if not success:
            return JSONResponse({"error": "Visite non trouvée"}, status_code=404)
        return {"message": "Visite supprimée avec succès"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
