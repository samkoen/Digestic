from app.repositories.base_repository import BaseRepository
from app.models.invoice import Invoice

class InvoiceRepository(BaseRepository[Invoice]):
    """Repository pour gérer les factures"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'invoices.json')
    
    def _model_from_dict(self, data: dict) -> Invoice:
        return Invoice.from_dict(data)
    
    def _model_to_dict(self, model: Invoice) -> dict:
        return model.to_dict()
    
    def find_by_pharmacy(self, pharmacy_id: str) -> list[Invoice]:
        """Trouve les factures d'une pharmacie"""
        return self.find_by(pharmacy_id=pharmacy_id)
    
    def find_overdue(self, days: int = 30) -> list[Invoice]:
        """Trouve les factures en retard de plus de X jours"""
        all_invoices = self.find_all()
        return [invoice for invoice in all_invoices 
                if invoice.status == 'overdue' and invoice.days_overdue >= days]


