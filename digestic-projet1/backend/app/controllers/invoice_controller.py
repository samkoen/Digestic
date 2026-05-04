from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.pagination import MAX_PAGE_SIZE
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.domain.pharmacy_notification_email import notification_email_for_pharmacy
from app.services.credit_note_service import CreditNoteService
from app.services.email_service import EmailService
from app.services.invoice_service import InvoiceService
from app.schemas.email_send import SendTransactionalEmailBody

router = APIRouter()


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(InvoiceRepository(db))


def get_credit_note_service(db: Session = Depends(get_db)) -> CreditNoteService:
    return CreditNoteService(db)


class PartialCreditLine(BaseModel):
    invoice_line_id: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)


class IssueCreditNoteBody(BaseModel):
    """Avoir total : seul `correction_reason`. Avoir partiel : ajouter `partial_lines`."""

    correction_reason: str = Field(..., min_length=3, max_length=2000)
    partial_lines: list[PartialCreditLine] | None = None


class MarkInvoicePaidBody(BaseModel):
    payment_date: str | None = Field(None, description="YYYY-MM-DD ; défaut = date du jour (serveur)")
    local_only: bool = Field(
        False,
        description=(
            "Si true : mise à jour Digestic uniquement, sans enregistrer le paiement sur VosFactures."
        ),
    )


@router.get("")
def get_invoices(
    page: int | None = Query(None, ge=1, description="Si présent, réponse paginée { items, total, … }"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE),
    sort: str = Query("issueDate"),
    order: str = Query("asc"),
    status: str | None = None,
    invoice_number: str | None = Query(None),
    pharmacy_name: str | None = Query(None),
    pharmacy_id: str | None = None,
    deposit_id: str | None = Query(None, description="Filtrer par id du dépôt / bon de livraison"),
    overdue_only: bool = Query(False),
    overdue_min_days: int = Query(0, ge=0, le=3650),
    overdue: bool = False,
    days: int = Query(default=30, ge=1),
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        if page is not None:
            pr = service.list_invoices_paginated(
                page=page,
                page_size=page_size,
                sort=sort,
                order=order,
                status=status,
                invoice_number=invoice_number,
                pharmacy_id=pharmacy_id,
                pharmacy_name=pharmacy_name,
                overdue_only=overdue_only,
                overdue_min_days=overdue_min_days,
                deposit_id=deposit_id,
            )
            return {
                "items": pr.items,
                "total": pr.total,
                "page": pr.page,
                "page_size": pr.page_size,
            }
        if overdue:
            invoices = service.get_overdue_invoices(days)
            return [invoice.to_dict() for invoice in invoices]
        if pharmacy_id:
            return service.get_pharmacy_invoice_table_rows(pharmacy_id)
        invoices = service.get_all_invoices()
        return [invoice.to_dict() for invoice in invoices]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
):
    """Télécharge le PDF depuis VosFactures (jeton API côté serveur uniquement)."""
    try:
        result = service.fetch_vosfactures_pdf(invoice_id)
        if result is None:
            return JSONResponse(
                {
                    "error": (
                        "PDF VosFactures indisponible (facture mock, autre fournisseur, "
                        "identifiant externe manquant ou VosFactures non configuré)."
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


@router.get("/{invoice_id}/credit-notes")
def list_credit_notes_for_invoice(
    invoice_id: str,
    cn_service: CreditNoteService = Depends(get_credit_note_service),
):
    try:
        return cn_service.list_for_invoice(invoice_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{invoice_id}/lines-for-credit")
def invoice_lines_for_credit(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
):
    """Lignes de facture utilisables pour composer un avoir partiel (quantités restantes)."""
    try:
        return service.list_invoice_lines_for_credit(invoice_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{invoice_id}/credit-notes", status_code=201)
def issue_credit_note_for_invoice(
    invoice_id: str,
    body: IssueCreditNoteBody,
    cn_service: CreditNoteService = Depends(get_credit_note_service),
):
    """Crée un avoir total ou partiel sur VosFactures et l’enregistre en base."""
    try:
        if body.partial_lines:
            specs = [
                {"invoice_line_id": str(p.invoice_line_id).strip(), "quantity": int(p.quantity)}
                for p in body.partial_lines
            ]
            return cn_service.issue_partial_credit_note(invoice_id, body.correction_reason, specs)
        return cn_service.issue_total_credit_note(invoice_id, body.correction_reason)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@router.post("/{invoice_id}/mark-paid")
def mark_invoice_paid(
    invoice_id: str,
    body: MarkInvoicePaidBody | None = None,
    service: InvoiceService = Depends(get_invoice_service),
):
    """Marque la facture comme payée (encaissement enregistré dans Digestic)."""
    try:
        pd = body.payment_date if body else None
        local_only = bool(body.local_only) if body else False
        inv = service.mark_invoice_paid(invoice_id, pd, skip_vosfactures=local_only)
        if not inv:
            return JSONResponse({"error": "Facture non trouvée"}, status_code=404)
        return inv.to_dict()
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = service.get_invoice_by_id(invoice_id)
        if not invoice:
            return JSONResponse({"error": "Facture non trouvée"}, status_code=404)
        return invoice.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_invoice(
    data: dict[str, Any],
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = service.create_invoice(data)
        return invoice.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{invoice_id}")
def update_invoice(
    invoice_id: str,
    data: dict[str, Any],
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        invoice = service.update_invoice(invoice_id, data)
        if not invoice:
            return JSONResponse({"error": "Facture non trouvée"}, status_code=404)
        return invoice.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/{invoice_id}/email-draft")
def get_invoice_email_draft(
    invoice_id: str,
    service: InvoiceService = Depends(get_invoice_service),
    db: Session = Depends(get_db),
):
    """Brouillon (destinataire + objet + HTML) depuis les modèles admin, sans envoi."""
    try:
        invoice = service.get_invoice_by_id(invoice_id)
        if not invoice:
            return JSONResponse({"error": "Facture non trouvée"}, status_code=404)
        pharmacy_repo = PharmacyRepository(db)
        pharmacy = pharmacy_repo.find_by_id(invoice.pharmacy_id)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        to_email = notification_email_for_pharmacy(pharmacy)
        if not to_email:
            return JSONResponse(
                {"error": "Aucun email enregistré pour cette pharmacie"},
                status_code=400,
            )
        email_service = EmailService(db)
        subject, body_html = email_service.prepare_invoice_email(
            pharmacy_name=pharmacy.name or "",
            invoice_number=invoice.invoice_number,
            invoice_amount=invoice.amount,
            invoice_date=invoice.issue_date,
            due_date=invoice.due_date,
        )
        return {"to_email": to_email, "subject": subject, "body_html": body_html}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{invoice_id}/send-email")
def send_invoice_email(
    invoice_id: str,
    body: SendTransactionalEmailBody = Body(default_factory=SendTransactionalEmailBody),
    service: InvoiceService = Depends(get_invoice_service),
    db: Session = Depends(get_db),
):
    try:
        invoice = service.get_invoice_by_id(invoice_id)
        if not invoice:
            return JSONResponse({"error": "Facture non trouvée"}, status_code=404)
        pharmacy_repo = PharmacyRepository(db)
        pharmacy = pharmacy_repo.find_by_id(invoice.pharmacy_id)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        to_email = notification_email_for_pharmacy(pharmacy)
        if not to_email:
            return JSONResponse(
                {"error": "Aucun email enregistré pour cette pharmacie"},
                status_code=400,
            )
        email_service = EmailService(db)
        if body.subject is not None or body.body_html is not None:
            if body.subject is None or body.body_html is None:
                return JSONResponse(
                    {"error": "Objet et corps HTML doivent être fournis ensemble."},
                    status_code=400,
                )
            try:
                success = email_service.send_custom_body(
                    to_email,
                    body.subject,
                    body.body_html,
                    kind="facture",
                )
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
        else:
            success = email_service.send_invoice_email(
                to_email,
                pharmacy_name=pharmacy.name or "",
                invoice_number=invoice.invoice_number,
                invoice_amount=invoice.amount,
                invoice_date=invoice.issue_date,
                due_date=invoice.due_date,
            )
        if success:
            return {
                "message": f"Facture envoyée avec succès à {to_email}",
                "email": to_email,
            }
        return JSONResponse(
            {"error": "Erreur lors de l'envoi de l'email"},
            status_code=500,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
