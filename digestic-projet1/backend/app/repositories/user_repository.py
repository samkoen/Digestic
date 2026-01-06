from app.repositories.base_repository import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository[User]):
    """Repository pour gérer les utilisateurs"""
    
    def __init__(self, data_dir: str):
        super().__init__(data_dir, 'users.json')
    
    def _model_from_dict(self, data: dict) -> User:
        return User.from_dict(data)
    
    def _model_to_dict(self, model: User) -> dict:
        return model.to_dict()
    
    def find_by_email(self, email: str):
        """Trouve un utilisateur par email"""
        results = self.find_by(email=email)
        return results[0] if results else None
    
    def find_by_role(self, role: str) -> list[User]:
        """Trouve les utilisateurs par rôle"""
        return self.find_by(role=role)


