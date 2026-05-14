"""Révisions des poids planning (JSON versionné), révision active et audit des runs."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.domain.visit_planning_engine import PlanningWeights

RUNTIME_ROW_ID = 1


def get_runtime_settings(db: Session) -> orm.PlanningRuntimeSettings | None:
    return db.get(orm.PlanningRuntimeSettings, RUNTIME_ROW_ID)


def get_active_revision(db: Session) -> orm.PlanningWeightsRevision | None:
    rt = get_runtime_settings(db)
    if rt is None or rt.active_revision_id is None:
        return None
    return db.get(orm.PlanningWeightsRevision, rt.active_revision_id)


def effective_weights_snapshot(db: Session) -> dict[str, Any]:
    active = get_active_revision(db)
    if active and active.weights:
        return dict(active.weights)
    return PlanningWeights.merge(None).__dict__.copy()


def build_combined_weights_mapping(
    db: Session,
    request_weights: dict[str, Any] | None,
) -> tuple[dict[str, Any], uuid.UUID | None, dict[str, Any]]:
    """Fusion révision active + surcharge HTTP éventuelle (les clés de la requête priment)."""
    active = get_active_revision(db)
    active_id = active.id if active else None
    base: dict[str, Any] = dict(active.weights) if active and active.weights else {}
    req = dict(request_weights or {})
    merged_flat = {**base, **req}
    return merged_flat, active_id, req


def normalize_weights_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Snapshot complet sérialisable (clés alignées sur PlanningWeights)."""
    return PlanningWeights.merge(raw).__dict__.copy()


def create_revision(
    db: Session,
    *,
    weights: dict[str, Any],
    label: str | None,
    created_by_user_id: uuid.UUID | None,
    set_active: bool,
) -> orm.PlanningWeightsRevision:
    snap = normalize_weights_payload(weights)
    next_num = db.scalar(
        select(func.coalesce(func.max(orm.PlanningWeightsRevision.revision_number), 0) + 1)
    )
    rev = orm.PlanningWeightsRevision(
        revision_number=int(next_num or 1),
        label=(label or "").strip() or None,
        weights=snap,
        created_by_user_id=created_by_user_id,
    )
    db.add(rev)
    db.flush()
    if set_active:
        set_active_revision_id(db, rev.id, commit=False)
    return rev


def set_active_revision_id(db: Session, revision_id: uuid.UUID, *, commit: bool = True) -> None:
    rev = db.get(orm.PlanningWeightsRevision, revision_id)
    if rev is None:
        raise ValueError("Révision introuvable.")
    rt = get_runtime_settings(db)
    if rt is None:
        db.add(orm.PlanningRuntimeSettings(id=RUNTIME_ROW_ID, active_revision_id=revision_id))
    else:
        rt.active_revision_id = revision_id
    if commit:
        db.commit()


def list_revisions(db: Session, *, limit: int = 100) -> list[orm.PlanningWeightsRevision]:
    q = (
        select(orm.PlanningWeightsRevision)
        .order_by(orm.PlanningWeightsRevision.revision_number.desc())
        .limit(limit)
    )
    return list(db.execute(q).scalars().all())


def list_planning_runs(db: Session, *, limit: int = 50) -> list[orm.PlanningRun]:
    q = select(orm.PlanningRun).order_by(orm.PlanningRun.created_at.desc()).limit(limit)
    return list(db.execute(q).scalars().all())


def record_planning_run(
    db: Session,
    *,
    run_id: uuid.UUID,
    reference_date: date,
    horizon_days: int,
    dry_run: bool,
    active_only: bool,
    scope_commercial_uuids: list[uuid.UUID] | None,
    active_revision_id_at_run: uuid.UUID | None,
    weights_request_override: dict[str, Any] | None,
    weights_effective: dict[str, Any],
    assignments_count: int,
    updated_count: int | None,
    skipped_manual_override_count: int,
    triggered_by_user_id: uuid.UUID | None,
) -> None:
    scope_json = None
    if scope_commercial_uuids is not None:
        scope_json = [str(x) for x in scope_commercial_uuids]
    override_json = weights_request_override if weights_request_override else None
    row = orm.PlanningRun(
        id=run_id,
        reference_date=reference_date,
        horizon_days=horizon_days,
        dry_run=dry_run,
        active_only=active_only,
        scope_commercial_ids=scope_json,
        active_revision_id_at_run=active_revision_id_at_run,
        weights_request_override=override_json,
        weights_effective=dict(weights_effective),
        assignments_count=assignments_count,
        updated_count=updated_count,
        skipped_manual_override_count=skipped_manual_override_count,
        triggered_by_user_id=triggered_by_user_id,
    )
    db.add(row)
