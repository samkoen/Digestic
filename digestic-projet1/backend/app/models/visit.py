from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class Visit:
    """Modèle représentant une visite planifiée"""
    id: str
    pharmacy_id: str
    commercial_id: str
    scheduled_date: str  # ISO format
    scheduled_time: Optional[str] = None
    status: str = "planned"  # planned, completed, cancelled, postponed
    notes: Optional[str] = None
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
        """Crée un objet Visit à partir d'un dictionnaire"""
        return cls(**data)


