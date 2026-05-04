from typing import Any, List, Optional

from datetime import date, datetime

from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository


class InvoiceService:
    """Service pour la gestion des factures"""
    
    def __init__(self, repository: InvoiceRepository):
        self.repository = repository
    
    def get_all_invoices(self) -> List[Invoice]:
        """Récupère toutes les factures"""
        return self.repository.find_all()
    
    def get_invoice_by_id(self, invoice_id: str) -> Optional[Invoice]:
        """Récupère une facture par son ID"""
        return self.repository.find_by_id(invoice_id)
    
    def create_invoice(self, invoice_data: dict) -> Invoice:
        """Crée une nouvelle facture"""
        import uuid
        invoice_data['id'] = str(uuid.uuid4())
        invoice = Invoice.from_dict(invoice_data)
        self._update_invoice_status(invoice)
        return self.repository.create(invoice)
    
    def update_invoice(self, invoice_id: str, invoice_data: dict) -> Optional[Invoice]:
        """Met à jour une facture"""
        existing = self.repository.find_by_id(invoice_id)
        if not existing:
            return None
        
        for key, value in invoice_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        existing.updated_at = datetime.now().isoformat()
        self._update_invoice_status(existing)
        
        return self.repository.update(invoice_id, existing)

    def mark_invoice_paid(
        self,
        invoice_id: str,
        payment_date_iso: str | None,
        *,
        skip_vosfactures: bool = False,
    ) -> Optional[Invoice]:
        """Marque une facture comme payée (saisie manuelle encaissement)."""
        existing = self.repository.find_by_id(invoice_id)
        if not existing:
            return None
        st = (existing.status or "").strip().lower()
        if st in ("credited", "cancelled"):
            raise ValueError(
                "Impossible de marquer comme payée une facture annulée "
                "ou déjà traitée comme créditée (avoir total)."
            )
        if st == "paid":
            raise ValueError("Cette facture est déjà indiquée comme payée.")
        pd = self._normalize_payment_date_input(payment_date_iso)
        if not skip_vosfactures:
            self._sync_vosfactures_invoice_payment(existing, pd)
        return self.update_invoice(
            invoice_id,
            {"status": "paid", "payment_date": pd, "days_overdue": 0},
        )

    def _sync_vosfactures_invoice_payment(self, invoice: Invoice, paid_date_iso: str) -> None:
        """Enregistre le paiement côté VosFactures avant mise à jour locale (digestic vf)."""
        prov = (invoice.external_provider or "").strip().lower()
        ext_id = (invoice.external_invoice_id or "").strip()
        if prov != "vosfactures" or not ext_id:
            return
        try:
            from app.integrations.vosfactures.config import vosfactures_is_configured
            from app.integrations.vosfactures.http_client import VosFacturesApiClient

            if not vosfactures_is_configured():
                return
            ttc = invoice.amount_ttc
            amt = float(ttc) if ttc is not None else float(invoice.amount)
            client = VosFacturesApiClient()
            inv_label = (invoice.invoice_number or "").strip()
            suffix = f" — {inv_label}" if inv_label else ""
            client.register_invoice_payment(
                vosfactures_invoice_id=ext_id,
                paid_date_iso=paid_date_iso,
                price_ttc=amt,
                payment_name=f"Encaissement Digestic{suffix}",
            )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(
                f"VosFactures : impossible d'enregistrer le paiement ({e!s}). "
                "Vérifiez la connexion et que la facture peut recevoir ce montant dans VosFactures."
            ) from e

    @staticmethod
    def _normalize_payment_date_input(raw: str | None) -> str:
        """Retourne une date ISO jour (YYYY-MM-DD), défaut aujourd'hui."""
        s = (raw or "").strip()
        if not s:
            return date.today().isoformat()
        chunk = s[:10]
        try:
            date.fromisoformat(chunk)
        except ValueError as e:
            raise ValueError("payment_date doit être au format YYYY-MM-DD.") from e
        return chunk

    def _update_invoice_status(self, invoice: Invoice):
        """Met à jour le statut d'une facture selon la date d'échéance"""
        due_date = datetime.fromisoformat(invoice.due_date)
        today = datetime.now()

        if invoice.status == "paid":
            return
        if invoice.status == "credited":
            return
        
        if today > due_date:
            days_overdue = (today - due_date).days
            invoice.days_overdue = days_overdue
            if days_overdue >= 30:
                invoice.status = 'overdue'
        else:
            invoice.days_overdue = 0
            if invoice.status == 'overdue':
                invoice.status = 'pending'
    
    def get_overdue_invoices(self, days: int = 30) -> List[Invoice]:
        """Récupère les factures en retard de plus de X jours"""
        all_invoices = self.repository.find_all()
        today = datetime.now()
        overdue = []
        
        for invoice in all_invoices:
            if invoice.status not in ("paid", "credited", "cancelled"):
                due_date = datetime.fromisoformat(invoice.due_date)
                if today > due_date:
                    days_overdue = (today - due_date).days
                    if days_overdue >= days:
                        invoice.days_overdue = days_overdue
                        overdue.append(invoice)
        
        return overdue
    
    def get_invoices_by_pharmacy(self, pharmacy_id: str) -> List[Invoice]:
        """Récupère les factures d'une pharmacie (modèles domaine)."""
        return self.repository.find_by_pharmacy(pharmacy_id)

    def get_pharmacy_invoice_table_rows(self, pharmacy_id: str) -> List[dict[str, Any]]:
        """Liste factures pharmacie enrichie (lignes BL, bouteilles payantes, remise) pour UI."""
        return self.repository.pharmacy_invoice_detail_dicts(pharmacy_id)

    def list_invoices_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "issueDate",
        order: str = "asc",
        status: str | None = None,
        invoice_number: str | None = None,
        pharmacy_id: str | None = None,
        pharmacy_name: str | None = None,
        overdue_only: bool = False,
        overdue_min_days: int = 0,
        deposit_id: str | None = None,
    ) -> Any:
        """Liste paginée avec tri et filtres (jointure pharmacie pour le nom)."""
        return self.repository.search_paginated(
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

    def list_invoice_lines_for_credit(self, invoice_id: str) -> List[dict[str, Any]]:
        """Lignes factures avec quantités encore créditables (avoir partiel)."""
        return self.repository.list_invoice_lines_for_credit(invoice_id)

    def fetch_vosfactures_pdf(self, invoice_id: str) -> tuple[bytes, str] | None:
        """Télécharge le PDF depuis VosFactures si facture émise via l’API réelle."""
        from app.integrations.vosfactures.config import vosfactures_is_configured
        from app.integrations.vosfactures.http_client import VosFacturesApiClient

        inv = self.repository.find_by_id(invoice_id)
        if not inv:
            return None
        if inv.external_provider != "vosfactures":
            return None
        if not inv.external_invoice_id:
            return None
        if not vosfactures_is_configured():
            return None
        client = VosFacturesApiClient()
        pdf = client.fetch_invoice_pdf(inv.external_invoice_id)
        base = (inv.invoice_number or inv.id).strip()
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in base)[:120]
        filename = f"{safe or 'facture'}.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"
        return pdf, filename
