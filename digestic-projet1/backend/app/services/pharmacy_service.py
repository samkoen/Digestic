from collections.abc import Sequence
from typing import Any, List, Optional

from app.models.pharmacy import Pharmacy
from app.repositories.pharmacy_comment_repository import PharmacyCommentRepository
from app.repositories.pharmacy_repository import PharmacyRepository


class PharmacyService:
    """Service pour la gestion des pharmacies"""

    def __init__(
        self,
        repository: PharmacyRepository,
        comment_repository: PharmacyCommentRepository,
    ):
        self.repository = repository
        self._comments = comment_repository

    def get_all_pharmacies(self) -> List[Pharmacy]:
        """Récupère toutes les pharmacies (usage interne / compat)."""
        return self.repository.find_all()

    def list_distinct_cities(self) -> List[str]:
        """Villes distinctes non vides (pour filtres multi-sélection)."""
        return self.repository.distinct_cities_sorted()

    def list_pharmacies_paginated(
        self,
        *,
        user_role: str | None,
        user_id: str | None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "name",
        order: str = "asc",
        name: str | None = None,
        address: str | None = None,
        commercial_id: str | Sequence[str] | None = None,
        last_visit: str | None = None,
        next_visit: str | None = None,
        pharmacy_status: str | None = None,
        city: str | Sequence[str] | None = None,
        postal_code: str | Sequence[str] | None = None,
        country: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        owner_name: str | None = None,
        payment_mode: str | Sequence[str] | None = None,
        created: str | None = None,
        rib: str | None = None,
        depot: str | None = None,
        warehouse_id: str | Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Liste paginée avec filtres et tri côté base ; commercial limité à ses pharmas."""
        restricted: str | None = None
        if user_role == "commercial" and user_id:
            restricted = str(user_id)
        pr = self.repository.search_paginated(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            name=name,
            address=address,
            commercial_id=commercial_id,
            last_visit=last_visit,
            next_visit=next_visit,
            pharmacy_status=pharmacy_status,
            city=city,
            postal_code=postal_code,
            country=country,
            email=email,
            phone=phone,
            owner_name=owner_name,
            payment_mode=payment_mode,
            created=created,
            rib=rib,
            depot=depot,
            warehouse_id=warehouse_id,
            restricted_to_commercial_id=restricted,
        )
        items: list[dict] = []
        for row in pr.items:
            d = row.pharmacy.to_dict()
            d["commercialName"] = row.commercial_name
            items.append(d)
        return {
            "items": items,
            "total": pr.total,
            "page": pr.page,
            "page_size": pr.page_size,
        }
    
    def get_pharmacy_by_id(self, pharmacy_id: str) -> Optional[Pharmacy]:
        """Récupère une pharmacie par son ID"""
        return self.repository.find_by_id(pharmacy_id)
    
    def create_pharmacy(self, pharmacy_data: dict) -> Pharmacy:
        """Crée une nouvelle pharmacie"""
        import uuid
        pharmacy_data['id'] = str(uuid.uuid4())
        pharmacy = Pharmacy.from_dict(pharmacy_data)
        return self.repository.create(pharmacy)
    
    def update_pharmacy(self, pharmacy_id: str, pharmacy_data: dict) -> Optional[Pharmacy]:
        """Met à jour une pharmacie"""
        existing = self.repository.find_by_id(pharmacy_id)
        if not existing:
            return None
        
        # Mise à jour des champs
        for key, value in pharmacy_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        return self.repository.update(pharmacy_id, existing)
    
    def delete_pharmacy(self, pharmacy_id: str) -> bool:
        """Supprime une pharmacie"""
        return self.repository.delete(pharmacy_id)

    def list_pharmacy_comments(self, pharmacy_id: str) -> Optional[List[dict[str, Any]]]:
        if not self.repository.find_by_id(pharmacy_id):
            return None
        return [c.to_dict() for c in self._comments.list_by_pharmacy(pharmacy_id)]

    def add_pharmacy_comment(self, pharmacy_id: str, text: str) -> Optional[dict[str, Any]]:
        if not self.repository.find_by_id(pharmacy_id):
            return None
        c = self._comments.create(pharmacy_id, text)
        if not c:
            return None
        return c.to_dict()

    def delete_pharmacy_comment(self, pharmacy_id: str, comment_id: str) -> bool:
        if not self.repository.find_by_id(pharmacy_id):
            return False
        return self._comments.delete(pharmacy_id, comment_id)

