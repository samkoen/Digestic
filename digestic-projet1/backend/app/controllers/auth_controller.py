import traceback
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/login")
def login(
    request: Request,
    data: dict[str, Any] | None = Body(default=None),
    service: AuthService = Depends(get_auth_service),
):
    try:
        if not data:
            return JSONResponse({"error": "Données manquantes"}, status_code=400)
        email = data.get("email")
        password = data.get("password")
        if not email:
            return JSONResponse({"error": "Email requis"}, status_code=400)
        if password is None or str(password).strip() == "":
            return JSONResponse({"error": "Mot de passe requis"}, status_code=400)
        user = service.authenticate(str(email).strip(), str(password))
        if not user:
            return JSONResponse(
                {"error": "Email ou mot de passe incorrect"},
                status_code=401,
            )
        request.session["user_id"] = user["id"]
        request.session["user_role"] = user["role"]
        request.session["user_email"] = user["email"]
        return {"message": "Connexion réussie", "user": user}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            {"error": f"Erreur serveur: {str(e)}"},
            status_code=500,
        )


@router.post("/logout")
def logout(request: Request):
    try:
        request.session.clear()
        return {"message": "Déconnexion réussie"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/me")
def get_current_user(
    request: Request,
    service: AuthService = Depends(get_auth_service),
):
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            return JSONResponse({"error": "Non authentifié"}, status_code=401)
        user = service.get_user_by_id(user_id)
        if not user:
            return JSONResponse({"error": "Utilisateur non trouvé"}, status_code=404)
        return {"user": user}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
