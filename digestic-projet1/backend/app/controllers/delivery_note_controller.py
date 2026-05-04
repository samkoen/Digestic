import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.auth.session_roles import require_admin_user_id
from app.domain.delivery_note_table_columns import DELIVERY_NOTE_SORT_KEYS
from app.pagination import MAX_PAGE_SIZE
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.delivery_note_service import DeliveryNoteService
from app.schemas.email_send import SendTransactionalEmailBody
from app.pdf.delivery_note_pdf import pdf_content_disposition_header

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
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("deliveryDate"),
    order: str = Query("desc"),
    pharmacy_id: list[str] | None = Query(None),
    commercial_id: list[str] | None = Query(None),
    status: str | None = None,
    delivery_date_from: str | None = None,
    delivery_date_to: str | None = None,
    deposit_id: str | None = None,
    pharmacy_name: str | None = None,
    include_archived: bool = Query(False),
    sage_reference: str | None = None,
    is_deposit_sale: bool | None = None,
    email_sent: str | None = None,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    try:
        if order.lower() not in ("asc", "desc"):
            order = "desc"
        skey = sort if sort in DELIVERY_NOTE_SORT_KEYS else "deliveryDate"
        role = request.session.get("user_role")
        uid = request.session.get("user_id")
        return service.list_delivery_notes_paginated(
            user_role=role,
            user_id_str=str(uid) if uid else None,
            page=page,
            page_size=page_size,
            sort=skey,
            order=order,
            pharmacy_id=pharmacy_id,
            commercial_id=commercial_id,
            status=status,
            delivery_date_from=delivery_date_from,
            delivery_date_to=delivery_date_to,
            deposit_id=deposit_id,
            pharmacy_name=pharmacy_name,
            include_archived=include_archived,
            sage_reference=sage_reference,
            is_deposit_sale=is_deposit_sale,
            email_sent=email_sent,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{note_id}/pdf")
def download_delivery_note_pdf(
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Télécharge le PDF du bon (mise en forme proche facture / BL Digestic)."""
    try:
        result = service.build_delivery_note_pdf(note_id)
        if not result:
            return JSONResponse(
                {"error": "Bon de livraison non trouvé"},
                status_code=404,
            )
        data, filename = result
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": pdf_content_disposition_header(filename)},
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{note_id}/email-draft")
def get_delivery_note_email_draft(
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Retourne le brouillon d’e-mail (modèle HTML admin) avant envoi — pas d’effet de bord."""
    try:
        return service.get_delivery_note_email_draft(note_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{note_id}/send-email")
def send_delivery_note_email(
    note_id: str,
    body: SendTransactionalEmailBody = Body(default_factory=SendTransactionalEmailBody),
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Envoie le BL par e-mail à l’adresse de la pharmacie (simulation sans SMTP si non configuré)."""
    try:
        return service.send_delivery_note_email_to_pharmacy(
            note_id,
            subject=body.subject,
            body_html=body.body_html,
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)
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


@router.post("/standalone", status_code=201)
def create_standalone_delivery_note(
    request: Request,
    data: dict[str, Any],
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Création d'un bon sans rapport de visite (stock + lignes comme après visite). Réservé admin."""
    require_admin_user_id(request)
    try:
        note = service.create_standalone_delivery_note_admin(dict(data))
        return note.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.exception("Création BL standalone")
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
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{note_id}/valider-depot-vente")
def validate_depot_vente_delivery_note(
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Dépôt-vente → en attente (pending), permet la facturation ultérieure."""
    try:
        note = service.validate_depot_vente_to_pending(note_id)
        if not note:
            return JSONResponse(
                {"error": "Bon de livraison non trouvé"},
                status_code=404,
            )
        return note.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{note_id}/annuler")
def annuler_delivery_note(
    request: Request,
    note_id: str,
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Annule un bon non facturé (stock remonté, statut cancelled). Admin uniquement."""
    uid = require_admin_user_id(request)
    try:
        note = service.cancel_delivery_note_admin(note_id, uid)
        return note.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.exception("Annulation BL %s", note_id)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{note_id}/rectifier", status_code=201)
def rectifier_delivery_note(
    request: Request,
    note_id: str,
    data: dict[str, Any] | None = Body(default=None),
    service: DeliveryNoteService = Depends(get_delivery_note_service),
):
    """Annule le bon source puis crée un bon rectificatif (même pharmacie). Admin uniquement."""
    uid = require_admin_user_id(request)
    try:
        return service.replace_delivery_note_with_rectified_admin(note_id, uid, dict(data or {}))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.exception("BL rectificatif %s", note_id)
        return JSONResponse({"error": str(e)}, status_code=400)
