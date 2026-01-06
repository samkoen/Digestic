from app.repositories.base_repository import BaseRepository
from app.models.pharmacy import Pharmacy

class PharmacyRepository(BaseRepository[Pharmacy]):
    """Repository pour gérer les pharmacies"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'pharmacies.json')
    
    def _model_from_dict(self, data: dict) -> Pharmacy:
        return Pharmacy.from_dict(data)
    
    def _model_to_dict(self, model: Pharmacy) -> dict:
        return model.to_dict()
    
    def find_by_classification(self, classification: str) -> list[Pharmacy]:
        """Trouve les pharmacies par classification"""
        return self.find_by(classification=classification)


