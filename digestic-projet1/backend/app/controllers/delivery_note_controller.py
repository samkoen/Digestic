import logging
from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.delivery_note_service import DeliveryNoteService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_delivery_note_service(db: Session = Depends(get_db)) -> DeliveryNoteService:
    return DeliveryNoteService(
        DeliveryNoteRepository(db),
        InvoiceRepository(db),
        PharmacyRepository(db),
        db,
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


def _coerce_bottles_to_invoice(raw: Any) -> int:
    """Entier ≥ 0 ; évite int(None) / int('') qui plantent ou renvoient des 400 peu clairs."""
    if raw is None or isinstance(raw, bool):
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return 0


def _coerce_amount(raw: Any) -> float:
    if raw is None or raw == "":
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _post_issue_invoice(
    note_id: str,
    data: dict[str, Any] | None,
    service: DeliveryNoteService,
):
    payload = data or {}
    bottles = _coerce_bottles_to_invoice(payload.get("bottles_to_invoice"))
    amount = _coerce_amount(payload.get("amount"))
    invoice, updated_note = service.issue_invoice_from_delivery_note(note_id, bottles, amount)
    return {
        "invoice": invoice.to_dict(),
        "delivery_note": updated_note.to_dict() if updated_note else None,
    }


@router.post("/{note_id}/facturer")
def issue_invoice_from_delivery_note(
    note_id: str,
    data: dict[str, Any] | None = Body(default=None),
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Émet la facture (Digestic + VosFactures / mock) pour ce bon de livraison."""
    try:
        return _post_issue_invoice(note_id, data, service)
    except ValueError as e:
        logger.info("Facturation BL %s refusée : %s", note_id, e)
        return JSONResponse({"error": str(e)}, status_code=400)
    except IntegrityError as e:
        logger.exception("Facturation BL %s : contrainte base", note_id)
        return JSONResponse(
            {
                "error": (
                    "Enregistrement impossible en base (ex. numéro de facture déjà utilisé). "
                    "Vérifiez les factures existantes ou réessayez."
                ),
                "detail": str(e.orig) if getattr(e, "orig", None) else str(e),
            },
            status_code=409,
        )
    except Exception as e:
        logger.exception("Facturation BL %s", note_id)
        return JSONResponse({"error": str(e)}, status_code=400)


@router.post("/{note_id}/convert")
def convert_delivery_note_legacy(
    note_id: str,
    data: dict[str, Any] | None = Body(default=None),
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Alias historique : préférer POST …/facturer."""
    try:
        return _post_issue_invoice(note_id, data, service)
    except ValueError as e:
        logger.info("Facturation BL %s (convert) refusée : %s", note_id, e)
        return JSONResponse({"error": str(e)}, status_code=400)
    except IntegrityError as e:
        logger.exception("Facturation BL %s (convert) : contrainte base", note_id)
        return JSONResponse(
            {
                "error": (
                    "Enregistrement impossible en base (ex. numéro de facture déjà utilisé). "
                    "Vérifiez les factures existantes ou réessayez."
                ),
                "detail": str(e.orig) if getattr(e, "orig", None) else str(e),
            },
            status_code=409,
        )
    except Exception as e:
        logger.exception("Facturation BL %s (convert)", note_id)
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
