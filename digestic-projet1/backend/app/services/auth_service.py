"""
Service d'authentification
"""
from typing import Optional

from app.core.security import verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    """Service pour l'authentification des utilisateurs"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def authenticate(self, email: str, password: str) -> Optional[dict]:
        """Vérifie email + mot de passe (bcrypt) ; retourne le profil public ou None."""
        plain = (password or "").strip()
        if not plain:
            return None

        user, pwd_hash = self.user_repository.get_user_and_password_hash(
            (email or "").strip()
        )
        if not user or not user.is_active:
            return None
        if not pwd_hash or not verify_password(plain, pwd_hash):
            return None

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "full_name": f"{user.first_name} {user.last_name}",
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


