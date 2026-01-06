from flask import Blueprint, request, jsonify, session
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository

auth_bp = Blueprint('auth', __name__)

def get_auth_service():
    from flask import current_app
    data_dir = current_app.config.get('DATA_DIR', 'data')
    repository = UserRepository(data_dir)
    return AuthService(repository)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authentifie un utilisateur"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données manquantes'}), 400
            
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email requis'}), 400
        
        service = get_auth_service()
        user = service.authenticate(email)
        
        if not user:
            return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
        
        # Créer une session
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        session['user_email'] = user['email']
        session.permanent = True
        
        return jsonify({
            'message': 'Connexion réussie',
            'user': user
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Déconnecte un utilisateur"""
    try:
        session.clear()
        return jsonify({'message': 'Déconnexion réussie'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Récupère l'utilisateur actuellement connecté"""
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'Non authentifié'}), 401
        
        service = get_auth_service()
        user = service.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        return jsonify({'user': user}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

