from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.db import mappers as mp
import app.db.models as orm
from app.repositories.pharmacy_advanced_filter_engine import (
    sanitize_pharmacy_advanced_filter_payload,
)
from app.domain.pharmacy_table_columns import PHARMACY_SORT_KEYS
from app.pagination import MAX_PAGE_SIZE
from app.repositories.pharmacy_comment_repository import PharmacyCommentRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.services.pharmacy_service import PharmacyService

router = APIRouter()


def get_pharmacy_service(db: Session = Depends(get_db)) -> PharmacyService:
    return PharmacyService(PharmacyRepository(db), PharmacyCommentRepository(db))


@router.get("")
def get_pharmacies(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Numéro de page (1-based)"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Taille de page"),
    sort: str = Query(
        "name",
        description="Champ de tri (whitelist côté serveur).",
    ),
    order: str = Query("asc", description="asc ou desc"),
    name: Optional[str] = Query(None, description="Filtre nom (contient)"),
    address: Optional[str] = Query(
        None, description="Filtre adresse (contient, concaténation en base)"
    ),
    commercial_id: Optional[list[str]] = Query(
        None,
        description="Filtre commercial(s) (UUID) ; répéter pour plusieurs (OU)",
    ),
    last_visit: Optional[str] = Query(
        None,
        description="Filtre dernière visite (sous-chaîne sur dates affichables / ISO)",
    ),
    next_visit: Optional[str] = Query(
        None, description="Filtre prochaine visite (YYYY-MM-DD, jour exact)"
    ),
    pharmacy_status: Optional[str] = Query(
        None, description="Filtre statut pharmacie (ex. actif, desactive)"
    ),
    city: Optional[list[str]] = Query(
        None,
        description="Filtre ville(s) (contient chaque terme) ; répéter pour plusieurs (OU)",
    ),
    postal_code: Optional[list[str]] = Query(
        None,
        description="Filtre code postal (contient) ; répéter le paramètre pour plusieurs valeurs (OU)",
    ),
    country: Optional[str] = Query(None, description="Filtre pays (contient)"),
    email: Optional[str] = Query(None, description="Filtre email (contient)"),
    phone: Optional[str] = Query(None, description="Filtre téléphone (contient)"),
    owner_name: Optional[str] = Query(
        None, description="Filtre titulaire (contient, owner_name)"
    ),
    payment_mode: Optional[list[str]] = Query(
        None,
        description="Mode(s) de paiement (valeur exacte) ; répéter pour plusieurs (OU)",
    ),
    created: Optional[str] = Query(
        None, description="Filtre date création (sous-chaîne ISO / affichage)"
    ),
    rib: Optional[str] = Query(
        None,
        description="RIB renseigné : yes/oui (présent) ou no/non (absent) ; omis = tous",
    ),
    depot: Optional[str] = Query(
        None, description="Filtre nom du dépôt (contient), ignoré si warehouse_id"
    ),
    warehouse_id: Optional[list[str]] = Query(
        None,
        description="UUID dépôt(s) ; répéter pour plusieurs (OU)",
    ),
    advanced_filter_id: Optional[str] = Query(
        None,
        description="UUID d’un filtre avancé enregistré (page Filtres liste pharmacies).",
    ),
):
    try:
        if order.lower() not in ("asc", "desc"):
            order = "asc"
        skey = sort if sort in PHARMACY_SORT_KEYS else "name"
        user_role = request.session.get("user_role")
        user_id = request.session.get("user_id")
        service = PharmacyService(
            PharmacyRepository(db),
            PharmacyCommentRepository(db),
        )
        adv_payload = None
        if advanced_filter_id and str(advanced_filter_id).strip():
            try:
                fid = mp.parse_uuid(str(advanced_filter_id).strip())
            except ValueError:
                fid = None
            if fid is not None:
                row = db.get(orm.PharmacyAdvancedFilter, fid)
                if row and isinstance(row.payload, dict):
                    adv_payload = sanitize_pharmacy_advanced_filter_payload(row.payload)
        return service.list_pharmacies_paginated(
            user_role=user_role,
            user_id=str(user_id) if user_id else None,
            page=page,
            page_size=page_size,
            sort=skey,
            order=order,
            name=name,
            address=address,
            commercial_id=commercial_id,
            last_visit=last_visit,
            next_visit=next_visit,
            pharmacy_status=pharmacy_status,
            city=city,
            postal_code=postal_code,
            country=country,
            email=email,
            phone=phone,
            owner_name=owner_name,
            payment_mode=payment_mode,
            created=created,
            rib=rib,
            depot=depot,
            warehouse_id=warehouse_id,
            advanced_filter_payload=adv_payload,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/distinct-cities")
def list_distinct_pharmacy_cities(
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        return service.list_distinct_cities()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/{pharmacy_id}/comments")
def list_pharmacy_comments(
    pharmacy_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        items = service.list_pharmacy_comments(pharmacy_id)
        if items is None:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return items
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/{pharmacy_id}/comments", status_code=201)
def create_pharmacy_comment(
    pharmacy_id: str,
    data: dict[str, Any],
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        text = (data or {}).get("text") or ""
        c = service.add_pharmacy_comment(pharmacy_id, text)
        if c is None and service.get_pharmacy_by_id(pharmacy_id) is None:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        if c is None:
            return JSONResponse(
                {"error": "Le commentaire ne peut pas être vide."}, status_code=400
            )
        return c
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{pharmacy_id}/comments/{comment_id}")
def delete_pharmacy_comment(
    pharmacy_id: str,
    comment_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        ok = service.delete_pharmacy_comment(pharmacy_id, comment_id)
        if not ok:
            if service.get_pharmacy_by_id(pharmacy_id) is None:
                return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
            return JSONResponse({"error": "Commentaire non trouvé"}, status_code=404)
        return {"message": "Commentaire supprimé"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/{pharmacy_id}")
def get_pharmacy(
    pharmacy_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.get_pharmacy_by_id(pharmacy_id)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("", status_code=201)
def create_pharmacy(
    data: dict[str, Any],
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.create_pharmacy(data)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.put("/{pharmacy_id}")
def update_pharmacy(
    pharmacy_id: str,
    data: dict[str, Any],
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        pharmacy = service.update_pharmacy(pharmacy_id, data)
        if not pharmacy:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return pharmacy.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.delete("/{pharmacy_id}")
def delete_pharmacy(
    pharmacy_id: str,
    service: PharmacyService = Depends(get_pharmacy_service),
):
    try:
        success = service.delete_pharmacy(pharmacy_id)
        if not success:
            return JSONResponse({"error": "Pharmacie non trouvée"}, status_code=404)
        return {"message": "Pharmacie supprimée avec succès"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
