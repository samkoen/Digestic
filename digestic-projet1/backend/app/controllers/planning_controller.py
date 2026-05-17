"""API du recalcul automatique des prochaines visites."""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

import app.db.models as orm
from app.auth.session_roles import ADMIN, require_user_id, session_user_role
from app.dependencies import get_db
from app.services.planning_evaluation_service import PlanningEvaluationService
from app.services.planning_weights_config_service import (
    build_combined_weights_mapping,
    create_revision,
    effective_weights_snapshot,
    list_planning_runs,
    list_revisions,
    record_planning_run,
    set_active_revision_id,
)
from app.services.pharmacy_planning_segments_service import (
    get_manual_planning_segment_mode,
    set_manual_planning_segment_mode,
    sync_segments_after_auto_planning_run,
)
from app.services.visit_planning_service import VisitPlanningService
from app.services.commercial_planning_calendar_service import (
    get_calendar_payload,
    replace_commercial_calendar,
)

router = APIRouter()

_EVAL_MAX_PERIOD_DAYS = 366


def _revision_payload(row: orm.PlanningWeightsRevision) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "revision_number": row.revision_number,
        "label": row.label,
        "weights": row.weights,
        "created_at": row.created_at.isoformat(),
        "created_by_user_id": str(row.created_by_user_id) if row.created_by_user_id else None,
    }


def _planning_run_payload(row: orm.PlanningRun) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "created_at": row.created_at.isoformat(),
        "reference_date": row.reference_date.isoformat(),
        "horizon_days": row.horizon_days,
        "dry_run": row.dry_run,
        "active_only": row.active_only,
        "scope_commercial_ids": row.scope_commercial_ids,
        "active_revision_id_at_run": str(row.active_revision_id_at_run)
        if row.active_revision_id_at_run
        else None,
        "weights_request_override": row.weights_request_override,
        "weights_effective": row.weights_effective,
        "assignments_count": row.assignments_count,
        "updated_count": row.updated_count,
        "skipped_manual_override_count": row.skipped_manual_override_count,
        "triggered_by_user_id": str(row.triggered_by_user_id)
        if row.triggered_by_user_id
        else None,
    }


class PlanningRunBody(BaseModel):
    reference_date: date | None = Field(
        default=None,
        description="Date de départ du planning (défaut : aujourd’hui UTC côté client).",
    )
    horizon_days: int = Field(default=7, ge=1, le=60)
    commercial_id: str | None = Field(
        default=None,
        description="Limiter à un commercial (UUID). Ignoré si `commercial_ids` est fourni avec au moins un id.",
    )
    commercial_ids: list[str] | None = Field(
        default=None,
        description=(
            "Admin uniquement — limiter au(x) commercial(aux) donnés (UUID). Les pharmacies sans commercial assigné "
            "ne sont jamais planifiées. Omission = tous les portefeuilles avec commercial."
        ),
    )
    dry_run: bool = False
    weights: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Surcharge optionnelle fusionnée avec la **révision active** (`planning_weights_revisions`). "
            "Omission = utiliser uniquement la révision active (ou défaut code si aucune)."
        ),
    )
    pharmacy_status_actif_only: bool = True

    @field_validator("weights", mode="before")
    @classmethod
    def _empty_weights(cls, v):
        if v == {}:
            return None
        return v


class CreatePlanningWeightsRevisionBody(BaseModel):
    weights: dict[str, Any]
    label: str | None = Field(default=None, description="Libellé métier (ex. « Essai mai »).")
    set_active: bool = Field(default=True, description="Définir cette révision comme active pour les runs sans surcharge.")


class SetActivePlanningWeightsRevisionBody(BaseModel):
    revision_id: str = Field(..., description="UUID de la révision à activer.")


class ManualPlanningSegmentModeBody(BaseModel):
    manual_planning_segment_mode: str = Field(
        ...,
        description="`inherit` (Mode A) ou `manual_revision` (Mode B) — cf. docs/planning_revision_segments_metier.md.",
    )


class WorkCalendarOffDateBody(BaseModel):
    date: date
    label: str | None = Field(default=None, max_length=255)


class WorkCalendarPutBody(BaseModel):
    """Journées fermées : weekday Python 0=lundi … 6=dimanche ; dates ISO pour fermetures ponctuelles."""

    off_weekdays: list[int] = Field(default_factory=list)
    off_dates: list[WorkCalendarOffDateBody] = Field(default_factory=list)

    @field_validator("off_weekdays", mode="after")
    @classmethod
    def _validate_weekdays(cls, v: list[int]) -> list[int]:
        for x in v:
            xi = int(x)
            if xi < 0 or xi > 6:
                raise ValueError("weekday doit être entre 0 (lundi) et 6 (dimanche).")
        return sorted({int(x) for x in v})


def _calendar_target_user_or_404(db: Session, cid: uuid.UUID) -> orm.User:
    u = db.get(orm.User, cid)
    if u is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")
    if (str(u.role or "").strip()).lower() != "commercial":
        raise HTTPException(
            status_code=400,
            detail="Le calendrier planning automatique concerne uniquement les comptes « commercial ».",
        )
    return u


def _enforce_work_calendar_access(request: Request, commercial_uuid: uuid.UUID) -> None:
    role = (session_user_role(request) or "").strip()
    uid = require_user_id(request)
    if role == ADMIN:
        return
    if role == "commercial":
        try:
            if uuid.UUID(str(uid).strip()) == commercial_uuid:
                return
        except ValueError:
            pass
        raise HTTPException(
            status_code=403,
            detail="Un commercial ne peut modifier que son propre calendrier.",
        )
    raise HTTPException(status_code=403, detail="Rôle non autorisé pour cette opération.")


@router.get("/work-calendar/{commercial_id}")
def get_planning_work_calendar(
    request: Request,
    commercial_id: str,
    db: Session = Depends(get_db),
):
    require_user_id(request)
    try:
        cid = uuid.UUID(str(commercial_id).strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="commercial_id invalide.") from e
    _enforce_work_calendar_access(request, cid)
    _calendar_target_user_or_404(db, cid)
    return get_calendar_payload(db, cid)


@router.put("/work-calendar/{commercial_id}")
def put_planning_work_calendar(
    request: Request,
    commercial_id: str,
    body: WorkCalendarPutBody,
    db: Session = Depends(get_db),
):
    require_user_id(request)
    try:
        cid = uuid.UUID(str(commercial_id).strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="commercial_id invalide.") from e
    _enforce_work_calendar_access(request, cid)
    _calendar_target_user_or_404(db, cid)
    pairs: list[tuple[date, str | None]] = [(o.date, o.label) for o in body.off_dates]
    replace_commercial_calendar(
        db,
        commercial_user_id=cid,
        off_weekdays=body.off_weekdays,
        off_dates_payload=pairs,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return get_calendar_payload(db, cid)


@router.post("/run")
def run_planning(
    request: Request,
    body: PlanningRunBody,
    db: Session = Depends(get_db),
):
    role = (session_user_role(request) or "").strip()
    uid = require_user_id(request)

    if role not in (ADMIN, "commercial"):
        raise HTTPException(
            status_code=403,
            detail="Rôle non autorisé pour cette opération.",
        )

    scope_commercial_uuids: list[uuid.UUID] | None = None
    if role == ADMIN:
        if body.commercial_ids is not None:
            if not body.commercial_ids:
                raise HTTPException(
                    status_code=400,
                    detail="commercial_ids est vide ; omettre le champ pour traiter tous les portefeuilles.",
                )
            try:
                scope_commercial_uuids = [
                    uuid.UUID(str(x).strip())
                    for x in body.commercial_ids
                    if str(x).strip()
                ]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            if not scope_commercial_uuids:
                raise HTTPException(
                    status_code=400,
                    detail="commercial_ids ne contient aucun UUID valide.",
                )
        elif body.commercial_id and str(body.commercial_id).strip():
            try:
                scope_commercial_uuids = [uuid.UUID(str(body.commercial_id).strip())]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        else:
            scope_commercial_uuids = None
    else:
        if body.commercial_id and str(body.commercial_id).strip() != str(uid).strip():
            raise HTTPException(
                status_code=403,
                detail="Un commercial ne peut lancer le planning que pour lui-même.",
            )
        try:
            scope_commercial_uuids = [uuid.UUID(str(uid))]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    ref = body.reference_date or date.today()
    combined, active_rev_id, req_override = build_combined_weights_mapping(db, body.weights)

    svc = VisitPlanningService(db)
    run_id = uuid.uuid4()
    try:
        result = svc.run_planning(
            reference_date=ref,
            horizon_days=int(body.horizon_days),
            scope_commercial_uuids=scope_commercial_uuids,
            weights_overrides=combined,
            dry_run=bool(body.dry_run),
            active_only=bool(body.pharmacy_status_actif_only),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    assignments_count = int(
        result.get("planned_count") if body.dry_run else result.get("updated_count") or 0
    )
    updated_ct = None if body.dry_run else result.get("updated_count")
    applied = dict(result.get("applied_weights") or {})

    record_planning_run(
        db,
        run_id=run_id,
        reference_date=ref,
        horizon_days=int(body.horizon_days),
        dry_run=bool(body.dry_run),
        active_only=bool(body.pharmacy_status_actif_only),
        scope_commercial_uuids=scope_commercial_uuids,
        active_revision_id_at_run=active_rev_id,
        weights_request_override=req_override if req_override else None,
        weights_effective=applied,
        assignments_count=assignments_count,
        updated_count=int(updated_ct) if updated_ct is not None else None,
        skipped_manual_override_count=int(result.get("skipped_manual_override_count") or 0),
        triggered_by_user_id=uuid.UUID(str(uid)),
    )
    db.flush()

    if not body.dry_run:
        raw_ids = result.get("assigned_pharmacy_ids") or []
        pids = []
        for x in raw_ids:
            try:
                pids.append(uuid.UUID(str(x)))
            except ValueError:
                continue
        if pids:
            sync_segments_after_auto_planning_run(
                db,
                pharmacy_ids=pids,
                segment_valid_from=ref,
                planning_run_id=run_id,
                baseline_revision_id=active_rev_id,
                weights_override_from_request=bool(req_override),
            )

    db.commit()

    result["planning_run"] = {
        "id": str(run_id),
        "active_revision_id_at_run": str(active_rev_id) if active_rev_id else None,
        "had_weights_override_in_request": bool(req_override),
    }
    return result


@router.get("/weights-config/active")
def get_active_planning_weights_config(request: Request, db: Session = Depends(get_db)):
    """Révision active + snapshot effectif (commercial ou admin). Distinct de la note terrain « v1 »."""
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role not in (ADMIN, "commercial"):
        raise HTTPException(status_code=403, detail="Rôle non autorisé.")

    active = None
    rt = db.get(orm.PlanningRuntimeSettings, 1)
    if rt and rt.active_revision_id:
        active = db.get(orm.PlanningWeightsRevision, rt.active_revision_id)

    eff = effective_weights_snapshot(db)
    mode = get_manual_planning_segment_mode(db)
    return {
        "active_revision": _revision_payload(active) if active else None,
        "effective_weights": eff,
        "manual_planning_segment_mode": mode,
        "note": "Les révisions ci-dessus concernent uniquement les poids du **moteur de planning**, pas la formule de note terrain v1.",
    }


@router.get("/runtime-config")
def get_planning_runtime_config(request: Request, db: Session = Depends(get_db)):
    """Mode manuel segments : Mode A (`inherit`) vs Mode B (`manual_revision`)."""
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role not in (ADMIN, "commercial"):
        raise HTTPException(status_code=403, detail="Rôle non autorisé.")
    return {"manual_planning_segment_mode": get_manual_planning_segment_mode(db)}


@router.put("/runtime-config")
def put_planning_runtime_config(
    request: Request,
    body: ManualPlanningSegmentModeBody,
    db: Session = Depends(get_db),
):
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role != ADMIN:
        raise HTTPException(status_code=403, detail="Admin uniquement.")
    try:
        set_manual_planning_segment_mode(
            db, body.manual_planning_segment_mode.strip(), commit=True
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {"manual_planning_segment_mode": get_manual_planning_segment_mode(db)}


@router.get("/weights-revisions")
def get_planning_weights_revisions_list(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role != ADMIN:
        raise HTTPException(status_code=403, detail="Admin uniquement.")
    rows = list_revisions(db, limit=limit)
    return {"revisions": [_revision_payload(r) for r in rows]}


@router.post("/weights-revisions")
def post_planning_weights_revision(
    request: Request,
    body: CreatePlanningWeightsRevisionBody,
    db: Session = Depends(get_db),
):
    role = (session_user_role(request) or "").strip()
    uid = require_user_id(request)
    if role != ADMIN:
        raise HTTPException(status_code=403, detail="Admin uniquement.")
    try:
        rev = create_revision(
            db,
            weights=body.weights,
            label=body.label,
            created_by_user_id=uuid.UUID(str(uid)),
            set_active=bool(body.set_active),
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return {"revision": _revision_payload(rev)}


@router.put("/weights-config/active")
def put_active_planning_weights_revision(
    request: Request,
    body: SetActivePlanningWeightsRevisionBody,
    db: Session = Depends(get_db),
):
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role != ADMIN:
        raise HTTPException(status_code=403, detail="Admin uniquement.")
    try:
        rid = uuid.UUID(str(body.revision_id).strip())
    except ValueError as e:
        raise HTTPException(status_code=400, detail="revision_id invalide.") from e
    try:
        set_active_revision_id(db, rid, commit=True)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    row = db.get(orm.PlanningWeightsRevision, rid)
    return {"active_revision": _revision_payload(row) if row else None}


@router.get("/runs")
def get_planning_runs_audit(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(default=40, ge=1, le=200),
):
    role = (session_user_role(request) or "").strip()
    require_user_id(request)
    if role != ADMIN:
        raise HTTPException(status_code=403, detail="Admin uniquement.")
    rows = list_planning_runs(db, limit=limit)
    return {"runs": [_planning_run_payload(r) for r in rows]}


@router.get("/evaluation")
def planning_evaluation_score(
    request: Request,
    db: Session = Depends(get_db),
    start_date: date = Query(..., description="Début inclus (visit_reports.visit_date)."),
    end_date: date = Query(..., description="Fin inclus."),
    commercial_id: str | None = Query(
        default=None,
        description="Admin uniquement : filtrer par commercial (UUID). Omis = tous.",
    ),
    planning_weights_revision_id: str | None = Query(
        default=None,
        description=(
            "Optionnel : ne garder que les rapports dont le segment planning actif ce jour-là "
            "pointe vers cette révision (`planning_weights_revisions.id`)."
        ),
    ),
    pure_auto_planning_weights_only: bool = Query(
        default=True,
        description="Si vrai : exclut segments manuels et segments auto avec surcharge HTTP `weights`.",
    ),
):
    """Note terrain figée **v1** sur une période (rapports de visite réels)."""
    role = (session_user_role(request) or "").strip()
    uid = require_user_id(request)

    if role not in (ADMIN, "commercial"):
        raise HTTPException(
            status_code=403,
            detail="Rôle non autorisé pour cette opération.",
        )

    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date doit précéder ou égaler end_date.")
    if (end_date - start_date).days > _EVAL_MAX_PERIOD_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Période trop longue (maximum {_EVAL_MAX_PERIOD_DAYS} jours).",
        )

    scope_cid: uuid.UUID | None = None
    if role == ADMIN:
        raw = (commercial_id or "").strip()
        if raw:
            try:
                scope_cid = uuid.UUID(raw)
            except ValueError as e:
                raise HTTPException(status_code=400, detail="commercial_id invalide.") from e
    else:
        try:
            scope_cid = uuid.UUID(str(uid))
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Identifiant utilisateur invalide.") from e

    rev_uuid: uuid.UUID | None = None
    raw_rev = (planning_weights_revision_id or "").strip()
    if raw_rev:
        try:
            rev_uuid = uuid.UUID(raw_rev)
        except ValueError as e:
            raise HTTPException(
                status_code=400, detail="planning_weights_revision_id invalide."
            ) from e

    svc = PlanningEvaluationService()
    return svc.evaluate_period(
        db,
        start=start_date,
        end=end_date,
        commercial_id=scope_cid,
        planning_weights_revision_id=rev_uuid,
        pure_auto_planning_weights_only=pure_auto_planning_weights_only,
    )


@router.get("/weights-defaults")
def planning_weights_defaults(request: Request):
    """Poids configurables utilisés par défaut par l'algorithme (documentation / UI)."""
    require_user_id(request)

    # Import léger évité avant usage
    from app.domain.visit_planning_engine import PlanningWeights

    w = PlanningWeights()
    docs: dict[str, str] = {
        "stock_out": "Rupture de stock rapportée sur le dernier rapport.",
        "stock_low": "Stock faible sur le dernier rapport.",
        "failed_closed": "Dernière tentative de visite = pharmacie fermée.",
        "failed_other": "Dernière visite non réalisée (autres motifs).",
        "per_day_overdue": 'Points/jour après la date « cible » (engagement absent → cycle depuis dernière visite).',
        "max_overdue_bonus": 'Plafond du bonus retard (cumul par jour avec per_day_overdue).',
        "in_target_week": "Bonus si le jour tombe dans la semaine ISO de l’engagement.",
        "geo_weight": "Faible coefficient : collage géographique autour du pôle du jour.",
        "fill_radius_km": "Km au-delà duquel la proximité contribue très peu.",
        "district_density": "Bonus léger lorsque le même « quartier » (CP+Ville court) est déjà chargé ce jour.",
        "visits_max_per_day": "Capacité par commercial et par jour.",
        "default_cycle_days": "Cycle par défaut si aucune date prochaine visite mais dernière visite connue.",
        "orphan_horizon_bonus_days": "Décalle doux sans historique.",
    }

    def _ftype(v):
        if isinstance(v, bool):
            return "bool"
        return type(v).__name__

    return {
        "weights": w.__dict__,
        "fields": [{"key": k, "value": getattr(w, k), "type_hint": _ftype(getattr(w, k)), "hint": docs.get(k, "")} for k in w.__dict__],
    }
