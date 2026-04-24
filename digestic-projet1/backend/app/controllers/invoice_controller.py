from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.email_service import EmailService
from app.services.invoice_service import InvoiceService

router = APIRouter()


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(InvoiceRepository(db))


@router.get("")
def get_invoices(
    pharmacy_id: str | None = None,
    overdue: bool = False,
    days: int = Query(default=30, ge=1),
    service: InvoiceService = Depends(get_invoice_service),
):
    try:
        if overdue:
            invoices = service.get_overdue_invoices(days)
        elif pharmacy_id:
            invoices = service.get_invoices_by_pharmacy(pharmacy_id)
        else:
            invoices = service.get_all_invoices()
        return [invoice.to_dict() for invoice in invoices]
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


@router.post("/{invoice_id}/send-email")
def send_invoice_email(
    invoice_id: str,
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
        to_email = pharmacy.email or pharmacy.pharmacist_email
        if not to_email:
            return JSONResponse(
                {"error": "Aucun email enregistré pour cette pharmacie"},
                status_code=400,
            )
        email_service = EmailService()
        success = email_service.send_invoice_email(
            to_email=to_email,
            pharmacy_name=pharmacy.name,
            invoice_number=invoice.invoice_number,
            invoice_amount=invoice.amount,
            invoice_date=invoice.issue_date,
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
