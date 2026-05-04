import dataclasses
from dataclasses import dataclass, asdict
from typing import Any, Optional
from datetime import datetime

@dataclass
class Invoice:
    """Modèle représentant une facture"""
    id: str
    pharmacy_id: str
    invoice_number: str
    amount: float
    issue_date: str  # ISO format
    due_date: str  # ISO format
    status: str = "pending"  # pending, paid, overdue, cancelled, credited
    payment_date: Optional[str] = None
    sage_reference: Optional[str] = None  # Référence dans Sage (quand intégré)
    deposit_id: Optional[str] = None
    visit_report_id: Optional[str] = None
    sale_date: Optional[str] = None
    billing_type: Optional[str] = None
    amount_ht: Optional[float] = None
    amount_vat: Optional[float] = None
    amount_ttc: Optional[float] = None
    external_provider: Optional[str] = None
    external_invoice_id: Optional[str] = None
    mock_provider_payload: Optional[dict[str, Any]] = None
    days_overdue: int = 0
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
        """Crée un objet Invoice à partir d'un dictionnaire"""
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})


