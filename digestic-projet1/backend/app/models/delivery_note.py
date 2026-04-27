import dataclasses
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class DeliveryNote:
    """Modèle représentant un bon de livraison"""
    id: str
    visit_report_id: str
    pharmacy_id: str
    commercial_id: str
    delivery_date: str  # ISO format
    bottles_count: int
    free_units_quantity: int = 0
    is_deposit_sale: bool = False
    status: str = "pending"  # pending, sent, confirmed
    sage_reference: Optional[str] = None  # Référence dans Sage (quand intégré)
    email_sent: bool = False
    email_sent_at: Optional[str] = None
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
        """Crée un objet DeliveryNote à partir d'un dictionnaire"""
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


