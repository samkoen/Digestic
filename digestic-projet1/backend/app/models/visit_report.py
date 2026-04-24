from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class VisitReport:
    """Modèle représentant un rapport de visite"""
    id: str
    pharmacy_id: str
    commercial_id: str
    visit_date: str  # ISO format
    visit_id: Optional[str] = None  # Optionnel : un rapport peut être créé sans visite planifiée
    visit_status: str = "completed"  # completed, not_completed
    visit_not_completed_reason: Optional[str] = None  # pharmacy_closed, owner_absent
    has_deposit: bool = False
    bottles_deposited: int = 0
    free_units: int = 0  # Nombre d'unités gratuites (UG)
    stock_status: str = "unknown"  # good, low, out_of_stock, unknown
    display_stand_status: str = "unknown"  # in_place, not_in_place, unknown
    covering_status: str = "unknown"  # in_place, to_order, unknown
    covering_size_to_order: Optional[str] = None
    next_visit_date: Optional[str] = None
    delivery_mode: str = "normal"  # normal, deposit_sale
    notes: Optional[str] = None
    synced: bool = False  # Pour le mode offline
    payment_mode: str = "encaissement sous 30 jours"
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
        """Crée un objet VisitReport à partir d'un dictionnaire"""
        return cls(**data)


