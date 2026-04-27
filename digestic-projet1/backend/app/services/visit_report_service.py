from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.payment_modes import DEFAULT_VISIT_REPORT_PAYMENT_MODE
from app.domain.billing import normalize_billing_type
from app.domain.expected_return_week import iso_week_and_year_after_n_weeks
from app.models.visit_report import VisitReport
from app.repositories.visit_report_repository import VisitReportRepository
from app.repositories.visit_repository import VisitRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.visit_billing_service import VisitBillingOrchestrator

class VisitReportService:
    """Service pour la gestion des rapports de visite"""
    
    def __init__(
        self,
        db: Session,
        visit_report_repo: VisitReportRepository,
        visit_repo: VisitRepository,
        pharmacy_repo: PharmacyRepository,
    ):
        self._db = db
        self.visit_report_repo = visit_report_repo
        self.visit_repo = visit_repo
        self.pharmacy_repo = pharmacy_repo
    
    def get_all_reports(self) -> List[VisitReport]:
        """Récupère tous les rapports"""
        return self.visit_report_repo.find_all()
    
    def get_report_by_id(self, report_id: str) -> Optional[VisitReport]:
        """Récupère un rapport par son ID"""
        return self.visit_report_repo.find_by_id(report_id)
    
    def create_report(self, report_data: dict) -> VisitReport:
        """Crée un nouveau rapport de visite"""
        import copy
        import uuid

        report_data = copy.deepcopy(report_data)
        report_data['id'] = str(uuid.uuid4())

        wk = report_data.pop('weeks_until_return', None)
        if wk is not None and str(wk).strip() != '':
            try:
                y, iso_w = iso_week_and_year_after_n_weeks(int(wk))
                report_data['expected_return_iso_year'] = y
                report_data['expected_return_iso_week'] = iso_w
            except (ValueError, TypeError):
                pass
        report_data.pop('next_visit_date', None)

        for k in ("voice_note_url", "photo_note_url", "video_note_url"):
            if report_data.get(k) == "":
                report_data[k] = None

        # Convertir bottles_deposited en int si c'est une chaîne
        if 'bottles_deposited' in report_data:
            try:
                report_data['bottles_deposited'] = int(report_data['bottles_deposited'])
            except (ValueError, TypeError):
                report_data['bottles_deposited'] = 0

        if 'free_units' in report_data:
            try:
                report_data['free_units'] = int(report_data['free_units'])
            except (ValueError, TypeError):
                report_data['free_units'] = 0

        if 'returns_quantity' in report_data:
            try:
                report_data['returns_quantity'] = int(report_data['returns_quantity'])
            except (ValueError, TypeError):
                report_data['returns_quantity'] = 0
        else:
            report_data['returns_quantity'] = 0

        report_data['billing_type'] = normalize_billing_type(report_data.get('billing_type'))
        rsrc = report_data.get('return_source_visit_report_id')
        if rsrc is not None and str(rsrc).strip() == '':
            report_data['return_source_visit_report_id'] = None

        if report_data.get('has_deposit') and report_data.get('bottles_deposited', 0) > 0:
            if not report_data.get('payment_mode'):
                pharmacy = self.pharmacy_repo.find_by_id(report_data.get('pharmacy_id'))
                if pharmacy and pharmacy.payment_mode:
                    report_data['payment_mode'] = pharmacy.payment_mode
                else:
                    report_data['payment_mode'] = DEFAULT_VISIT_REPORT_PAYMENT_MODE

        report = VisitReport.from_dict(report_data)
        saved = self.visit_report_repo.create(report)

        needs_billing = (
            saved.has_deposit and (saved.bottles_deposited > 0 or saved.free_units > 0)
        ) or (getattr(saved, "returns_quantity", 0) or 0) > 0
        if needs_billing:
            VisitBillingOrchestrator(self._db).run_after_visit_report_persisted(saved)

        if saved.visit_id:
            visit = self.visit_repo.find_by_id(saved.visit_id)
            if visit:
                visit.status = "completed"
                self.visit_repo.update(visit.id, visit)

        return saved
    
    def update_report(self, report_id: str, report_data: dict) -> Optional[VisitReport]:
        """Met à jour un rapport"""
        import copy

        existing = self.visit_report_repo.find_by_id(report_id)
        if not existing:
            return None

        report_data = copy.deepcopy(report_data)
        wk = report_data.pop('weeks_until_return', None)
        if wk is not None and str(wk).strip() != '':
            try:
                y, iso_w = iso_week_and_year_after_n_weeks(int(wk))
                report_data['expected_return_iso_year'] = y
                report_data['expected_return_iso_week'] = iso_w
            except (ValueError, TypeError):
                pass
        report_data.pop('next_visit_date', None)

        for k in ("voice_note_url", "photo_note_url", "video_note_url"):
            if k in report_data and report_data.get(k) == "":
                report_data[k] = None

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

    def get_reports_by_commercial(self, commercial_id: str) -> List[VisitReport]:
        return self.visit_report_repo.find_by_commercial(commercial_id)

    def get_reports_by_pharmacy(self, pharmacy_id: str) -> List[VisitReport]:
        return self.visit_report_repo.find_by_pharmacy(pharmacy_id)
    
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


