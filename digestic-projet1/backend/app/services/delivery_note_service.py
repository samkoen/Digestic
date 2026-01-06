from typing import List, Optional
from app.models.delivery_note import DeliveryNote
from app.repositories.delivery_note_repository import DeliveryNoteRepository

class DeliveryNoteService:
    """Service pour la gestion des bons de livraison"""
    
    def __init__(self, repository: DeliveryNoteRepository):
        self.repository = repository
    
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


