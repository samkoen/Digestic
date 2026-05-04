"""PDF avoir (VosFactures) — identifiant avoir Digestic."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.credit_note_service import CreditNoteService

router = APIRouter()


def get_credit_note_service(db: Session = Depends(get_db)) -> CreditNoteService:
    return CreditNoteService(db)


@router.get("/{credit_note_id}/pdf")
def download_credit_note_pdf(
    credit_note_id: str,
    service: CreditNoteService = Depends(get_credit_note_service),
):
    """Télécharge le PDF de l’avoir depuis VosFactures (même endpoint que facture, autre id)."""
    try:
        result = service.fetch_credit_note_pdf(credit_note_id)
        if result is None:
            return JSONResponse(
                {
                    "error": (
                        "PDF indisponible (mock, identifiant externe manquant "
                        "ou VosFactures non configuré)."
                    )
                },
                status_code=404,
            )
        data, filename = result
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
