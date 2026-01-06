from flask import Blueprint, request, jsonify
from app.services.pharmacy_service import PharmacyService
from app.repositories.pharmacy_repository import PharmacyRepository
from app.models.pharmacy import Pharmacy

pharmacy_bp = Blueprint('pharmacy', __name__)

# Initialisation des services (sera injecté via app context ou config)
def get_pharmacy_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    repository = PharmacyRepository(data_dir)
    return PharmacyService(repository)

@pharmacy_bp.route('', methods=['GET'])
def get_pharmacies():
    """Récupère toutes les pharmacies (filtrées selon le rôle)"""
    try:
        from flask import session
        
        service = get_pharmacy_service()
        classification = request.args.get('classification')
        
        # Récupérer le rôle de l'utilisateur connecté
        user_role = session.get('user_role')
        user_id = session.get('user_id')
        
        if user_role == 'commercial' and user_id:
            # Les commerciaux ne voient que leurs pharmacies
            all_pharmacies = service.get_all_pharmacies()
            pharmacies = [p for p in all_pharmacies if p.commercial_id == user_id]
        else:
            # Les admins voient tout
            if classification:
                pharmacies = service.get_pharmacies_by_classification(classification)
            else:
                pharmacies = service.get_all_pharmacies()
        
        return jsonify([pharmacy.to_dict() for pharmacy in pharmacies]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pharmacy_bp.route('/<pharmacy_id>', methods=['GET'])
def get_pharmacy(pharmacy_id):
    """Récupère une pharmacie par son ID"""
    try:
        service = get_pharmacy_service()
        pharmacy = service.get_pharmacy_by_id(pharmacy_id)
        
        if not pharmacy:
            return jsonify({'error': 'Pharmacie non trouvée'}), 404
        
        return jsonify(pharmacy.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pharmacy_bp.route('', methods=['POST'])
def create_pharmacy():
    """Crée une nouvelle pharmacie"""
    try:
        data = request.get_json()
        service = get_pharmacy_service()
        pharmacy = service.create_pharmacy(data)
        return jsonify(pharmacy.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pharmacy_bp.route('/<pharmacy_id>', methods=['PUT'])
def update_pharmacy(pharmacy_id):
    """Met à jour une pharmacie"""
    try:
        data = request.get_json()
        service = get_pharmacy_service()
        pharmacy = service.update_pharmacy(pharmacy_id, data)
        
        if not pharmacy:
            return jsonify({'error': 'Pharmacie non trouvée'}), 404
        
        return jsonify(pharmacy.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@pharmacy_bp.route('/<pharmacy_id>', methods=['DELETE'])
def delete_pharmacy(pharmacy_id):
    """Supprime une pharmacie"""
    try:
        service = get_pharmacy_service()
        success = service.delete_pharmacy(pharmacy_id)
        
        if not success:
            return jsonify({'error': 'Pharmacie non trouvée'}), 404
        
        return jsonify({'message': 'Pharmacie supprimée avec succès'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

