from flask import Blueprint, request, jsonify
from app.repositories.user_repository import UserRepository

user_bp = Blueprint('user', __name__)

def get_user_repository():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    return UserRepository(data_dir)

@user_bp.route('', methods=['GET'])
def get_users():
    """Récupère tous les utilisateurs"""
    try:
        repo = get_user_repository()
        role = request.args.get('role')
        
        if role:
            users = repo.find_by_role(role)
        else:
            users = repo.find_all()
        
        return jsonify([user.to_dict() for user in users]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/<user_id>', methods=['GET'])
def get_user(user_id):
    """Récupère un utilisateur par son ID"""
    try:
        repo = get_user_repository()
        user = repo.find_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('', methods=['POST'])
def create_user():
    """Crée un nouvel utilisateur"""
    try:
        data = request.get_json()
        import uuid
        data['id'] = str(uuid.uuid4())
        
        repo = get_user_repository()
        user = repo._model_from_dict(data)
        user = repo.create(user)
        
        return jsonify(user.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@user_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Met à jour un utilisateur"""
    try:
        data = request.get_json()
        repo = get_user_repository()
        existing = repo.find_by_id(user_id)
        
        if not existing:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        
        from datetime import datetime
        existing.updated_at = datetime.now().isoformat()
        
        user = repo.update(user_id, existing)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@user_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Supprime un utilisateur"""
    try:
        repo = get_user_repository()
        success = repo.delete(user_id)
        
        if not success:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify({'message': 'Utilisateur supprimé avec succès'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

