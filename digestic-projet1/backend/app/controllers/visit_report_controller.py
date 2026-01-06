from flask import Blueprint, request, jsonify
from app.services.visit_report_service import VisitReportService
from app.repositories.visit_report_repository import VisitReportRepository
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.visit_repository import VisitRepository

visit_report_bp = Blueprint('visit_report', __name__)

def get_visit_report_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    visit_report_repo = VisitReportRepository(data_dir)
    delivery_note_repo = DeliveryNoteRepository(data_dir)
    visit_repo = VisitRepository(data_dir)
    return VisitReportService(visit_report_repo, delivery_note_repo, visit_repo)

@visit_report_bp.route('', methods=['GET'])
def get_visit_reports():
    """Récupère tous les rapports de visite"""
    try:
        service = get_visit_report_service()
        commercial_id = request.args.get('commercial_id')
        pharmacy_id = request.args.get('pharmacy_id')
        unsynced = request.args.get('unsynced', 'false').lower() == 'true'
        
        if unsynced:
            reports = service.get_unsynced_reports()
        elif commercial_id:
            reports = service.visit_report_repo.find_by_commercial(commercial_id)
        elif pharmacy_id:
            reports = service.visit_report_repo.find_by_pharmacy(pharmacy_id)
        else:
            reports = service.get_all_reports()
        
        return jsonify([report.to_dict() for report in reports]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@visit_report_bp.route('/<report_id>', methods=['GET'])
def get_visit_report(report_id):
    """Récupère un rapport de visite par son ID"""
    try:
        service = get_visit_report_service()
        report = service.get_report_by_id(report_id)
        
        if not report:
            return jsonify({'error': 'Rapport non trouvé'}), 404
        
        return jsonify(report.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@visit_report_bp.route('', methods=['POST'])
def create_visit_report():
    """Crée un nouveau rapport de visite"""
    try:
        data = request.get_json()
        service = get_visit_report_service()
        report = service.create_report(data)
        return jsonify(report.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@visit_report_bp.route('/<report_id>', methods=['PUT'])
def update_visit_report(report_id):
    """Met à jour un rapport de visite"""
    try:
        data = request.get_json()
        service = get_visit_report_service()
        report = service.update_report(report_id, data)
        
        if not report:
            return jsonify({'error': 'Rapport non trouvé'}), 404
        
        return jsonify(report.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@visit_report_bp.route('/sync', methods=['POST'])
def sync_reports():
    """Synchronise les rapports non synchronisés"""
    try:
        service = get_visit_report_service()
        count = service.sync_reports()
        return jsonify({'message': f'{count} rapports synchronisés'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


