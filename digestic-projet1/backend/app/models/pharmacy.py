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
    warehouse_id: str | None = None  # dépôt (warehouses) ; requis côté PostgreSQL
    depot_name: str | None = None  # nom du dépôt (lecture seule, jointure)
    depot_type: str | None = None  # central | secondaire (lecture seule)
    country: str | None = None
    email: str | None = None  # email principal pharmacie (API)
    phone: str | None = None  # téléphone établissement (DB pharmacies.phone)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pharmacist_name: Optional[str] = None
    pharmacist_email: Optional[str] = None
    pharmacist_phone: Optional[str] = None
    rib: Optional[str] = None  # RIB (Relevé d'Identité Bancaire)
    status: str = "actif"  # actif, desactive, standby, autre, … (Sage TYPE / règles métier)
    commercial_id: Optional[str] = None  # ID du commercial assigné
    last_visit_at: Optional[str] = None  # dernière visite (ISO, aligné sur last_visit_at en base)
    next_visit_date: Optional[str] = None  # Date de la prochaine visite (ISO format)
    photo_url: Optional[str] = None
    payment_mode: str = "virement 30 jours"
    reduction: float = 0.0  # pourcentage 0–100 (HT), appliqué BL et facturation dépôt
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
            'id', 'name', 'address', 'city', 'postal_code', 'warehouse_id', 'country', 'email', 'phone',
            'latitude', 'longitude', 'pharmacist_name', 'pharmacist_email', 'pharmacist_phone',
            'rib', 'status', 'commercial_id', 'last_visit_at', 'next_visit_date', 'photo_url', 'payment_mode',
            'reduction', 'reduction_percent',
            'created_at', 'updated_at'
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        rp = filtered_data.pop("reduction_percent", None)
        if "reduction" not in filtered_data and rp is not None:
            filtered_data["reduction"] = rp
        if "status" in filtered_data and (filtered_data["status"] is None or filtered_data["status"] == ""):
            del filtered_data["status"]
        # Ancien booléen API
        if "status" not in filtered_data and "active" in data:
            a = data.get("active")
            if a is False or (isinstance(a, str) and a.strip().lower() in ("false", "0", "non", "no")):
                filtered_data["status"] = "desactive"
            elif a is True or a in (None,):
                filtered_data["status"] = "actif"
        if "status" in filtered_data and isinstance(filtered_data["status"], str):
            filtered_data["status"] = filtered_data["status"].strip().lower()[:32] or "actif"
        return cls(**filtered_data)

