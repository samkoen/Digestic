from flask import Blueprint, request, jsonify
from app.services.visit_service import VisitService
from app.repositories.visit_repository import VisitRepository

visit_bp = Blueprint('visit', __name__)

def get_visit_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    repository = VisitRepository(data_dir)
    return VisitService(repository)

@visit_bp.route('', methods=['GET'])
def get_visits():
    """Récupère toutes les visites"""
    try:
        from datetime import datetime
        service = get_visit_service()
        commercial_id = request.args.get('commercial_id')
        pharmacy_id = request.args.get('pharmacy_id')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Récupérer toutes les visites
        if commercial_id:
            visits = service.get_visits_by_commercial(commercial_id)
        elif pharmacy_id:
            visits = service.get_visits_by_pharmacy(pharmacy_id)
        else:
            visits = service.get_all_visits()
        
        # Filtrer par statut si fourni
        if status:
            visits = [v for v in visits if v.status == status]
        
        # Filtrer par date si fourni
        if start_date or end_date:
            filtered_visits = []
            for visit in visits:
                if not visit.scheduled_date:
                    continue
                
                visit_date = datetime.fromisoformat(visit.scheduled_date.replace('Z', '+00:00'))
                
                if start_date:
                    start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    if visit_date < start:
                        continue
                
                if end_date:
                    end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    if visit_date > end:
                        continue
                
                filtered_visits.append(visit)
            visits = filtered_visits
        
        return jsonify([visit.to_dict() for visit in visits]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@visit_bp.route('/<visit_id>', methods=['GET'])
def get_visit(visit_id):
    """Récupère une visite par son ID"""
    try:
        service = get_visit_service()
        visit = service.get_visit_by_id(visit_id)
        
        if not visit:
            return jsonify({'error': 'Visite non trouvée'}), 404
        
        return jsonify(visit.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@visit_bp.route('', methods=['POST'])
def create_visit():
    """Crée une nouvelle visite"""
    try:
        data = request.get_json()
        service = get_visit_service()
        visit = service.create_visit(data)
        return jsonify(visit.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@visit_bp.route('/<visit_id>', methods=['PUT'])
def update_visit(visit_id):
    """Met à jour une visite"""
    try:
        data = request.get_json()
        service = get_visit_service()
        visit = service.update_visit(visit_id, data)
        
        if not visit:
            return jsonify({'error': 'Visite non trouvée'}), 404
        
        return jsonify(visit.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@visit_bp.route('/<visit_id>', methods=['DELETE'])
def delete_visit(visit_id):
    """Supprime une visite"""
    try:
        service = get_visit_service()
        success = service.delete_visit(visit_id)
        
        if not success:
            return jsonify({'error': 'Visite non trouvée'}), 404
        
        return jsonify({'message': 'Visite supprimée avec succès'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


