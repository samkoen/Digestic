from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.delivery_note_service import DeliveryNoteService
from app.services.invoice_service import InvoiceService

router = APIRouter()


def get_delivery_note_service(db: Session = Depends(get_db)) -> DeliveryNoteService:
    return DeliveryNoteService(
        DeliveryNoteRepository(db),
        InvoiceService(InvoiceRepository(db)),
    )


@router.get("")
def get_delivery_notes(
    pharmacy_id: str | None = None,
    commercial_id: str | None = None,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        if pharmacy_id:
            notes = service.get_delivery_notes_by_pharmacy(pharmacy_id)
        elif commercial_id:
            notes = service.get_delivery_notes_by_commercial(commercial_id)
        else:
            notes = service.get_all_delivery_notes()
        return [note.to_dict() for note in notes]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{note_id}")
def get_delivery_note(
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        note = service.get_delivery_note_by_id(note_id)
        if not note:
            return JSONResponse(
                {"error": "Bon de livraison non trouvé"},
                status_code=404,
            )
        return note.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_delivery_note(
    data: dict[str, Any],
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        note = service.create_delivery_note(data)
        return note.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{note_id}/convert")
def convert_delivery_note(
    note_id: str,
    data: dict[str, Any] | None = Body(default=None),
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        payload = data or {}
        bottles = int(payload.get("bottles_to_invoice", 0))
        amount = float(payload.get("amount", 0))
        invoice, updated_note = service.convert_to_invoice(note_id, bottles, amount)
        return {
            "invoice": invoice.to_dict(),
            "delivery_note": updated_note.to_dict() if updated_note else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{note_id}/send")
def send_delivery_note(
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        note = service.mark_as_sent(note_id)
        if not note:
            return JSONResponse(
                {"error": "Bon de livraison non trouvé"},
                status_code=404,
            )
        return note.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
