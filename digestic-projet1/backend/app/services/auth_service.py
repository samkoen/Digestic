"""
Service d'authentification
"""
from typing import Optional
from app.repositories.user_repository import UserRepository

class AuthService:
    """Service pour l'authentification des utilisateurs"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def authenticate(self, email: str, password: str = None) -> Optional[dict]:
        """
        Authentifie un utilisateur par email
        
        Args:
            email: Email de l'utilisateur
            password: Mot de passe (pour l'instant non utilisé, à implémenter plus tard)
        
        Returns:
            Dictionnaire avec les informations de l'utilisateur ou None
        """
        user = self.user_repository.find_by_email(email)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        # Pour l'instant, on accepte sans vérification de mot de passe
        # Plus tard, ajouter la vérification du hash du mot de passe
        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'full_name': f"{user.first_name} {user.last_name}"
        }
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Récupère un utilisateur par son ID"""
        user = self.user_repository.find_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        return {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'full_name': f"{user.first_name} {user.last_name}"
        }


