from typing import List, Optional
from app.models.visit import Visit
from app.repositories.visit_repository import VisitRepository

class VisitService:
    """Service pour la gestion des visites"""
    
    def __init__(self, repository: VisitRepository):
        self.repository = repository
    
    def get_all_visits(self) -> List[Visit]:
        """Récupère toutes les visites"""
        return self.repository.find_all()
    
    def get_visit_by_id(self, visit_id: str) -> Optional[Visit]:
        """Récupère une visite par son ID"""
        return self.repository.find_by_id(visit_id)
    
    def create_visit(self, visit_data: dict) -> Visit:
        """Crée une nouvelle visite"""
        import uuid
        visit_data['id'] = str(uuid.uuid4())
        visit = Visit.from_dict(visit_data)
        return self.repository.create(visit)
    
    def update_visit(self, visit_id: str, visit_data: dict) -> Optional[Visit]:
        """Met à jour une visite"""
        existing = self.repository.find_by_id(visit_id)
        if not existing:
            return None
        
        for key, value in visit_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        return self.repository.update(visit_id, existing)
    
    def delete_visit(self, visit_id: str) -> bool:
        """Supprime une visite"""
        return self.repository.delete(visit_id)
    
    def get_visits_by_commercial(self, commercial_id: str) -> List[Visit]:
        """Récupère les visites d'un commercial"""
        return self.repository.find_by_commercial(commercial_id)
    
    def get_visits_by_pharmacy(self, pharmacy_id: str) -> List[Visit]:
        """Récupère les visites d'une pharmacie"""
        return self.repository.find_by_pharmacy(pharmacy_id)


