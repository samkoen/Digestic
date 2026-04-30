from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.pagination import MAX_PAGE_SIZE
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.email_service import EmailService
from app.services.invoice_service import InvoiceService

router = APIRouter()


def get_invoice_service(db: Session = Depends(get_db)) -> InvoiceService:
    return InvoiceService(InvoiceRepository(db))


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
                "items": [
                    {**inv.to_dict(), "pharmacy_name": pname or "", "bl_number": bln or ""}
                    for inv, pname, bln in pr.items
                ],
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
