from flask import Blueprint, request, jsonify
from app.repositories.commercial_material_repository import CommercialMaterialRepository

commercial_material_bp = Blueprint('commercial_material', __name__)

def get_commercial_material_repository():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    return CommercialMaterialRepository(data_dir)

@commercial_material_bp.route('', methods=['GET'])
def get_commercial_materials():
    """Récupère tous les supports commerciaux"""
    try:
        repo = get_commercial_material_repository()
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        if active_only:
            materials = repo.find_active()
        else:
            materials = repo.find_all()
        
        return jsonify([material.to_dict() for material in materials]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@commercial_material_bp.route('/<material_id>', methods=['GET'])
def get_commercial_material(material_id):
    """Récupère un support commercial par son ID"""
    try:
        repo = get_commercial_material_repository()
        material = repo.find_by_id(material_id)
        
        if not material:
            return jsonify({'error': 'Support commercial non trouvé'}), 404
        
        return jsonify(material.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@commercial_material_bp.route('', methods=['POST'])
def create_commercial_material():
    """Crée un nouveau support commercial"""
    try:
        data = request.get_json()
        import uuid
        data['id'] = str(uuid.uuid4())
        
        repo = get_commercial_material_repository()
        material = repo._model_from_dict(data)
        material = repo.create(material)
        
        return jsonify(material.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@commercial_material_bp.route('/<material_id>', methods=['PUT'])
def update_commercial_material(material_id):
    """Met à jour un support commercial"""
    try:
        data = request.get_json()
        repo = get_commercial_material_repository()
        existing = repo.find_by_id(material_id)
        
        if not existing:
            return jsonify({'error': 'Support commercial non trouvé'}), 404
        
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        material = repo.update(material_id, existing)
        return jsonify(material.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


