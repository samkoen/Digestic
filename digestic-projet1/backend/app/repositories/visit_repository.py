from app.repositories.base_repository import BaseRepository
from app.models.visit import Visit

class VisitRepository(BaseRepository[Visit]):
    """Repository pour gérer les visites"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'visits.json')
    
    def _model_from_dict(self, data: dict) -> Visit:
        return Visit.from_dict(data)
    
    def _model_to_dict(self, model: Visit) -> dict:
        return model.to_dict()
    
    def find_by_commercial(self, commercial_id: str) -> list[Visit]:
        """Trouve les visites d'un commercial"""
        return self.find_by(commercial_id=commercial_id)
    
    def find_by_pharmacy(self, pharmacy_id: str) -> list[Visit]:
        """Trouve les visites d'une pharmacie"""
        return self.find_by(pharmacy_id=pharmacy_id)
    
    def find_by_status(self, status: str) -> list[Visit]:
        """Trouve les visites par statut"""
        return self.find_by(status=status)


