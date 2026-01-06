from app.repositories.base_repository import BaseRepository
from app.models.commercial_material import CommercialMaterial

class CommercialMaterialRepository(BaseRepository[CommercialMaterial]):
    """Repository pour gérer les supports commerciaux"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'commercial_materials.json')
    
    def _model_from_dict(self, data: dict) -> CommercialMaterial:
        return CommercialMaterial.from_dict(data)
    
    def _model_to_dict(self, model: CommercialMaterial) -> dict:
        return model.to_dict()
    
    def find_active(self) -> list[CommercialMaterial]:
        """Trouve les supports commerciaux actifs"""
        all_materials = self.find_all()
        return [material for material in all_materials if material.is_active]


