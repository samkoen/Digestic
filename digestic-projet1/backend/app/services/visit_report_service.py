from typing import List, Optional
from app.models.visit_report import VisitReport
from app.repositories.visit_report_repository import VisitReportRepository
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.visit_repository import VisitRepository

class VisitReportService:
    """Service pour la gestion des rapports de visite"""
    
    def __init__(self, visit_report_repo: VisitReportRepository, 
                 delivery_note_repo: DeliveryNoteRepository,
                 visit_repo: VisitRepository):
        self.visit_report_repo = visit_report_repo
        self.delivery_note_repo = delivery_note_repo
        self.visit_repo = visit_repo
    
    def get_all_reports(self) -> List[VisitReport]:
        """Récupère tous les rapports"""
        return self.visit_report_repo.find_all()
    
    def get_report_by_id(self, report_id: str) -> Optional[VisitReport]:
        """Récupère un rapport par son ID"""
        return self.visit_report_repo.find_by_id(report_id)
    
    def create_report(self, report_data: dict) -> VisitReport:
        """Crée un nouveau rapport de visite"""
        import uuid
        report_data['id'] = str(uuid.uuid4())
        
        # Convertir bottles_deposited en int si c'est une chaîne
        if 'bottles_deposited' in report_data:
            try:
                report_data['bottles_deposited'] = int(report_data['bottles_deposited'])
            except (ValueError, TypeError):
                report_data['bottles_deposited'] = 0
        
        report = VisitReport.from_dict(report_data)
        
        # Si dépôt, créer automatiquement un bon de livraison
        if report.has_deposit and report.bottles_deposited > 0:
            self._create_delivery_note(report)
        
        # Marquer la visite comme complétée
        if report.visit_id:
            visit = self.visit_repo.find_by_id(report.visit_id)
            if visit:
                visit.status = 'completed'
                self.visit_repo.update(visit.id, visit)
        
        return self.visit_report_repo.create(report)
    
    def _create_delivery_note(self, report: VisitReport):
        """Crée un bon de livraison à partir d'un rapport"""
        import uuid
        delivery_note_data = {
            'id': str(uuid.uuid4()),
            'visit_report_id': report.id,
            'pharmacy_id': report.pharmacy_id,
            'commercial_id': report.commercial_id,
            'delivery_date': report.visit_date,
            'bottles_count': report.bottles_deposited,
            'is_deposit_sale': report.delivery_mode == 'deposit_sale'
        }
        delivery_note = self.delivery_note_repo._model_from_dict(delivery_note_data)
        self.delivery_note_repo.create(delivery_note)
    
    def update_report(self, report_id: str, report_data: dict) -> Optional[VisitReport]:
        """Met à jour un rapport"""
        existing = self.visit_report_repo.find_by_id(report_id)
        if not existing:
            return None
        
        for key, value in report_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        existing.synced = True  # Marquer comme synchronisé lors de la mise à jour
        
        return self.visit_report_repo.update(report_id, existing)
    
    def get_unsynced_reports(self) -> List[VisitReport]:
        """Récupère les rapports non synchronisés (mode offline)"""
        return self.visit_report_repo.find_unsynced()
    
    def sync_reports(self) -> int:
        """Synchronise tous les rapports non synchronisés"""
        unsynced = self.get_unsynced_reports()
        count = 0
        for report in unsynced:
            report.synced = True
            from datetime import datetime
            report.updated_at = datetime.now().isoformat()
            self.visit_report_repo.update(report.id, report)
            count += 1
        return count


