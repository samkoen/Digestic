from typing import List, Optional
from app.models.pharmacy import Pharmacy
from app.repositories.pharmacy_repository import PharmacyRepository

class PharmacyService:
    """Service pour la gestion des pharmacies"""
    
    def __init__(self, repository: PharmacyRepository):
        self.repository = repository
    
    def get_all_pharmacies(self) -> List[Pharmacy]:
        """Récupère toutes les pharmacies"""
        return self.repository.find_all()
    
    def get_pharmacy_by_id(self, pharmacy_id: str) -> Optional[Pharmacy]:
        """Récupère une pharmacie par son ID"""
        return self.repository.find_by_id(pharmacy_id)
    
    def create_pharmacy(self, pharmacy_data: dict) -> Pharmacy:
        """Crée une nouvelle pharmacie"""
        import uuid
        pharmacy_data['id'] = str(uuid.uuid4())
        pharmacy = Pharmacy.from_dict(pharmacy_data)
        return self.repository.create(pharmacy)
    
    def update_pharmacy(self, pharmacy_id: str, pharmacy_data: dict) -> Optional[Pharmacy]:
        """Met à jour une pharmacie"""
        existing = self.repository.find_by_id(pharmacy_id)
        if not existing:
            return None
        
        # Mise à jour des champs
        for key, value in pharmacy_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        return self.repository.update(pharmacy_id, existing)
    
    def delete_pharmacy(self, pharmacy_id: str) -> bool:
        """Supprime une pharmacie"""
        return self.repository.delete(pharmacy_id)
    
    def get_pharmacies_by_classification(self, classification: str) -> List[Pharmacy]:
        """Récupère les pharmacies par classification"""
        return self.repository.find_by_classification(classification)


