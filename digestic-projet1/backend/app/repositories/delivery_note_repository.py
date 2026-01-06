from app.repositories.base_repository import BaseRepository
from app.models.delivery_note import DeliveryNote

class DeliveryNoteRepository(BaseRepository[DeliveryNote]):
    """Repository pour gérer les bons de livraison"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'delivery_notes.json')
    
    def _model_from_dict(self, data: dict) -> DeliveryNote:
        return DeliveryNote.from_dict(data)
    
    def _model_to_dict(self, model: DeliveryNote) -> dict:
        return model.to_dict()
    
    def find_by_pharmacy(self, pharmacy_id: str) -> list[DeliveryNote]:
        """Trouve les bons de livraison d'une pharmacie"""
        return self.find_by(pharmacy_id=pharmacy_id)
    
    def find_by_commercial(self, commercial_id: str) -> list[DeliveryNote]:
        """Trouve les bons de livraison d'un commercial"""
        return self.find_by(commercial_id=commercial_id)
    
    def find_pending(self) -> list[DeliveryNote]:
        """Trouve les bons de livraison en attente"""
        return self.find_by(status='pending')


