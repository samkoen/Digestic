from typing import List, Optional
from app.models.visit import Visit
from app.models.pharmacy import Pharmacy
from app.services.visit_service import VisitService
from app.services.pharmacy_service import PharmacyService

class VisitBusiness:
    """Couche métier pour la gestion des visites et optimisation des itinéraires"""
    
    def __init__(self, visit_service: VisitService, pharmacy_service: PharmacyService):
        self.visit_service = visit_service
        self.pharmacy_service = pharmacy_service
    
    def optimize_route(self, pharmacy_ids: List[str], start_location: Optional[dict] = None) -> List[str]:
        """
        Optimise l'itinéraire de visite basé sur les pharmacies et leur classification.
        Utilise un algorithme simple de plus proche voisin.
        
        Args:
            pharmacy_ids: Liste des IDs de pharmacies à visiter
            start_location: Position de départ {'latitude': float, 'longitude': float}
        
        Returns:
            Liste ordonnée des IDs de pharmacies pour l'itinéraire optimisé
        """
        if not pharmacy_ids:
            return []
        
        pharmacies = []
        for pharm_id in pharmacy_ids:
            pharmacy = self.pharmacy_service.get_pharmacy_by_id(pharm_id)
            if pharmacy and pharmacy.latitude and pharmacy.longitude:
                pharmacies.append(pharmacy)
        
        if not pharmacies:
            return pharmacy_ids  # Retourne l'ordre original si pas de coordonnées
        
        # Trier par classification (A > B > C) puis par distance
        pharmacies.sort(key=lambda p: (
            {'A': 0, 'B': 1, 'C': 2}.get(p.classification, 3),
            p.latitude or 0,
            p.longitude or 0
        ))
        
        # Algorithme du plus proche voisin si on a une position de départ
        if start_location and start_location.get('latitude') and start_location.get('longitude'):
            optimized = []
            remaining = pharmacies.copy()
            current_lat = start_location['latitude']
            current_lon = start_location['longitude']
            
            while remaining:
                # Trouver la pharmacie la plus proche
                closest = min(remaining, key=lambda p: 
                    self._calculate_distance(
                        current_lat, current_lon,
                        p.latitude, p.longitude
                    )
                )
                optimized.append(closest.id)
                remaining.remove(closest)
                current_lat = closest.latitude
                current_lon = closest.longitude
            
            return optimized
        
        # Sinon, retourner trié par classification
        return [p.id for p in pharmacies]
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcule la distance approximative entre deux points (formule de Haversine simplifiée)"""
        # Approximation simple pour la distance
        return ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5
    
    def suggest_next_visit_date(self, pharmacy_id: str, last_visit_date: Optional[str] = None) -> str:
        """
        Suggère une date de prochaine visite basée sur la classification de la pharmacie
        
        Args:
            pharmacy_id: ID de la pharmacie
            last_visit_date: Date de la dernière visite (ISO format)
        
        Returns:
            Date suggérée pour la prochaine visite (ISO format)
        """
        from datetime import datetime, timedelta
        
        pharmacy = self.pharmacy_service.get_pharmacy_by_id(pharmacy_id)
        if not pharmacy:
            # Par défaut, 30 jours
            return (datetime.now() + timedelta(days=30)).isoformat()
        
        # Fréquence selon classification
        frequency_days = {
            'A': 15,  # Visites fréquentes pour les pharmacies prioritaires
            'B': 30,
            'C': 45
        }
        
        days = frequency_days.get(pharmacy.classification, 30)
        
        if last_visit_date:
            last_date = datetime.fromisoformat(last_visit_date)
            next_date = last_date + timedelta(days=days)
        else:
            next_date = datetime.now() + timedelta(days=days)
        
        return next_date.isoformat()


