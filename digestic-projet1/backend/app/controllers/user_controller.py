import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.user_repository import UserRepository

router = APIRouter()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.get("")
def get_users(
    role: str | None = None,
    repo: UserRepository = Depends(get_user_repository),
):
    try:
        if role:
            users = repo.find_by_role(role)
        else:
            users = repo.find_all()
        return [user.to_dict() for user in users]
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{user_id}")
def get_user(
    user_id: str,
    repo: UserRepository = Depends(get_user_repository),
):
    try:
        user = repo.find_by_id(user_id)
        if not user:
            return JSONResponse({"error": "Utilisateur non trouvé"}, status_code=404)
        return user.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_user(
    data: dict[str, Any],
    repo: UserRepository = Depends(get_user_repository),
):
    try:
        data = dict(data)
        data["id"] = str(uuid.uuid4())
        user = repo._model_from_dict(data)
        user = repo.create(user)
        return user.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{user_id}")
def update_user(
    user_id: str,
    data: dict[str, Any],
    repo: UserRepository = Depends(get_user_repository),
):
    try:
        existing = repo.find_by_id(user_id)
        if not existing:
            return JSONResponse({"error": "Utilisateur non trouvé"}, status_code=404)
        for key, value in data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)
        existing.updated_at = datetime.now().isoformat()
        user = repo.update(user_id, existing)
        return user.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    repo: UserRepository = Depends(get_user_repository),
):
    try:
        success = repo.delete(user_id)
        if not success:
            return JSONResponse({"error": "Utilisateur non trouvé"}, status_code=404)
        return {"message": "Utilisateur supprimé avec succès"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
