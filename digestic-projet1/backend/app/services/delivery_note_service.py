from typing import List, Optional
from app.models.delivery_note import DeliveryNote
from app.models.invoice import Invoice
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.invoice_service import InvoiceService
from datetime import datetime, timedelta

class DeliveryNoteService:
    """Service pour la gestion des bons de livraison"""

    def __init__(self, repository: DeliveryNoteRepository, invoice_service: InvoiceService):
        self.repository = repository
        self.invoice_service = invoice_service
    
    def get_all_delivery_notes(self) -> List[DeliveryNote]:
        """Récupère tous les bons de livraison"""
        return self.repository.find_all()
    
    def get_delivery_note_by_id(self, note_id: str) -> Optional[DeliveryNote]:
        """Récupère un bon de livraison par son ID"""
        return self.repository.find_by_id(note_id)
    
    def create_delivery_note(self, note_data: dict) -> DeliveryNote:
        """Crée un nouveau bon de livraison"""
        import uuid
        note_data['id'] = str(uuid.uuid4())
        note = DeliveryNote.from_dict(note_data)
        return self.repository.create(note)
    
    def update_delivery_note(self, note_id: str, note_data: dict) -> Optional[DeliveryNote]:
        """Met à jour un bon de livraison"""
        existing = self.repository.find_by_id(note_id)
        if not existing:
            return None
        
        for key, value in note_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        return self.repository.update(note_id, existing)
    
    def mark_as_sent(self, note_id: str) -> Optional[DeliveryNote]:
        """Marque un bon de livraison comme envoyé par email"""
        from datetime import datetime
        return self.update_delivery_note(note_id, {
            'email_sent': True,
            'email_sent_at': datetime.now().isoformat(),
            'status': 'sent'
        })
    
    def get_delivery_notes_by_pharmacy(self, pharmacy_id: str) -> List[DeliveryNote]:
        """Récupère les bons de livraison d'une pharmacie"""
        return self.repository.find_by_pharmacy(pharmacy_id)

    def convert_to_invoice(self, note_id: str, bottles_to_invoice: int, amount: float) -> tuple[Invoice, DeliveryNote|None]:
        note = self.repository.find_by_id(note_id)
        if not note:
            raise ValueError('Bon de livraison introuvable')
        if bottles_to_invoice <= 0 or bottles_to_invoice > note.bottles_count:
            raise ValueError('Quantité invalide')

        invoice_data = {
            'pharmacy_id': note.pharmacy_id,
            'invoice_number': f"BL-{note.id[:6]}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount': amount,
            'issue_date': datetime.now().isoformat(),
            'due_date': (datetime.now() + timedelta(days=30)).isoformat(),
            'status': 'pending',
        }
        invoice = self.invoice_service.create_invoice(invoice_data)

        remainder = note.bottles_count - bottles_to_invoice
        if remainder > 0:
            note.bottles_count = remainder
            note.updated_at = datetime.now().isoformat()
            self.repository.update(note.id, note)
            next_note = note
        else:
            self.repository.delete(note.id)
            next_note = None

        return invoice, next_note

    def get_delivery_notes_by_commercial(self, commercial_id: str) -> List[DeliveryNote]:
        """Récupère les bons de livraison d'un commercial"""
        return self.repository.find_by_commercial(commercial_id)


