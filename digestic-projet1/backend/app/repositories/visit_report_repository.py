from app.repositories.base_repository import BaseRepository
from app.models.visit_report import VisitReport

class VisitReportRepository(BaseRepository[VisitReport]):
    """Repository pour gérer les rapports de visite"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'visit_reports.json')
    
    def _model_from_dict(self, data: dict) -> VisitReport:
        return VisitReport.from_dict(data)
    
    def _model_to_dict(self, model: VisitReport) -> dict:
        return model.to_dict()
    
    def find_by_commercial(self, commercial_id: str) -> list[VisitReport]:
        """Trouve les rapports d'un commercial"""
        return self.find_by(commercial_id=commercial_id)
    
    def find_by_pharmacy(self, pharmacy_id: str) -> list[VisitReport]:
        """Trouve les rapports d'une pharmacie"""
        return self.find_by(pharmacy_id=pharmacy_id)
    
    def find_unsynced(self) -> list[VisitReport]:
        """Trouve les rapports non synchronisés (mode offline)"""
        all_reports = self.find_all()
        return [report for report in all_reports if not report.synced]


