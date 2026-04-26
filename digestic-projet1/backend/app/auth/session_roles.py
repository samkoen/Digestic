"""Vérification du rôle admin via session (Starlette / FastAPI)."""
from __future__ import annotations

from fastapi import HTTPException, Request, status

ADMIN = "admin"


def session_user_role(request: Request) -> str | None:
    r = request.session.get("user_role")
    return str(r) if r else None


def require_user_id(request: Request) -> str:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
        )
    return str(uid)


def require_admin_user_id(request: Request) -> str:
    if session_user_role(request) != ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Réservé aux administrateurs",
        )
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide",
        )
    return str(uid)
