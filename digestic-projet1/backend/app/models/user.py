from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class User:
    """Modèle représentant un utilisateur (commercial ou administrateur)"""
    id: str
    email: str
    first_name: str
    last_name: str
    role: str = "commercial"  # commercial, admin
    phone: Optional[str] = None
    is_active: bool = True
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
        """Crée un objet User à partir d'un dictionnaire"""
        return cls(**data)


