from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class Pharmacy:
    """Modèle représentant une pharmacie"""
    id: str
    name: str
    address: str
    city: str
    postal_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pharmacist_name: Optional[str] = None
    pharmacist_email: Optional[str] = None
    pharmacist_phone: Optional[str] = None
    rib: Optional[str] = None  # RIB (Relevé d'Identité Bancaire)
    classification: str = "C"  # A, B, C ou urbaine, rurale
    commercial_id: Optional[str] = None  # ID du commercial assigné
    next_visit_date: Optional[str] = None  # Date de la prochaine visite (ISO format)
    created_at: str = None
    updated_at: str = None
    
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
        """Crée un objet Pharmacy à partir d'un dictionnaire"""
        # Filtrer les champs valides pour éviter les erreurs
        valid_fields = {
            'id', 'name', 'address', 'city', 'postal_code', 'latitude', 
            'longitude', 'pharmacist_name', 'pharmacist_email', 'pharmacist_phone',
            'rib', 'classification', 'commercial_id', 'next_visit_date', 'created_at', 'updated_at'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)

