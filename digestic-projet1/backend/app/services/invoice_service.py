from typing import List, Optional
from datetime import datetime, timedelta
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
    
    def _update_invoice_status(self, invoice: Invoice):
        """Met à jour le statut d'une facture selon la date d'échéance"""
        due_date = datetime.fromisoformat(invoice.due_date)
        today = datetime.now()
        
        if invoice.status == 'paid':
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
            if invoice.status != 'paid':
                due_date = datetime.fromisoformat(invoice.due_date)
                if today > due_date:
                    days_overdue = (today - due_date).days
                    if days_overdue >= days:
                        invoice.days_overdue = days_overdue
                        overdue.append(invoice)
        
        return overdue
    
    def get_invoices_by_pharmacy(self, pharmacy_id: str) -> List[Invoice]:
        """Récupère les factures d'une pharmacie"""
        return self.repository.find_by_pharmacy(pharmacy_id)


