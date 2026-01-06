from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class CommercialMaterial:
    """Modèle représentant un support commercial"""
    id: str
    name: str
    type: str  # product_sheet, clinical_study, marketing_material
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0"
    is_active: bool = True
    updated_at: str = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self):
        """Convertit l'objet en dictionnaire"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Crée un objet CommercialMaterial à partir d'un dictionnaire"""
        return cls(**data)


