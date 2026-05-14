"""Segments [valid_from, valid_to) : révision planning par pharmacie (+ manuel Mode B)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import desc, or_, select, update
from sqlalchemy.orm import Session

import app.db.models as orm
from app.planning_revision_constants import MANUAL_PLANNING_WEIGHTS_REVISION_ID


def get_manual_planning_segment_mode(db: Session) -> str:
    rt = db.get(orm.PlanningRuntimeSettings, 1)
    if rt is None:
        return "inherit"
    m = (rt.manual_planning_segment_mode or "").strip()
    return m if m in ("inherit", "manual_revision") else "inherit"


def set_manual_planning_segment_mode(db: Session, mode: str, *, commit: bool = False) -> None:
    if mode not in ("inherit", "manual_revision"):
        raise ValueError("manual_planning_segment_mode invalide.")
    rt = db.get(orm.PlanningRuntimeSettings, 1)
    if rt is None:
        db.add(orm.PlanningRuntimeSettings(id=1, manual_planning_segment_mode=mode))
    else:
        rt.manual_planning_segment_mode = mode
    if commit:
        db.commit()


def _close_open_segment(db: Session, pharmacy_id: uuid.UUID, valid_to_exclusive: date) -> None:
    db.execute(
        update(orm.PharmacyPlanningRevisionSegment)
        .where(
            orm.PharmacyPlanningRevisionSegment.pharmacy_id == pharmacy_id,
            orm.PharmacyPlanningRevisionSegment.valid_to.is_(None),
        )
        .values(valid_to=valid_to_exclusive)
    )


def sync_segments_after_auto_planning_run(
    db: Session,
    *,
    pharmacy_ids: list[uuid.UUID],
    segment_valid_from: date,
    planning_run_id: uuid.UUID | None,
    baseline_revision_id: uuid.UUID | None,
    weights_override_from_request: bool,
) -> None:
    """À chaque run auto appliqué : fermeture segment ouvert + nouveau segment."""
    for pid in pharmacy_ids:
        _close_open_segment(db, pid, segment_valid_from)
        db.add(
            orm.PharmacyPlanningRevisionSegment(
                pharmacy_id=pid,
                valid_from=segment_valid_from,
                valid_to=None,
                planning_weights_revision_id=baseline_revision_id,
                planning_run_id=planning_run_id,
                segment_source="auto",
                weights_override_from_request=weights_override_from_request,
            )
        )


def maybe_record_manual_next_visit_segment(
    db: Session,
    *,
    pharmacy_id: uuid.UUID,
    previous_next_visit_date: date | None,
    new_next_visit_date: date | None,
    effective_date: date,
) -> None:
    """Mode B (`manual_revision`) : nouvelle ligne sous révision sentinel « manuel »."""
    if previous_next_visit_date == new_next_visit_date:
        return
    if get_manual_planning_segment_mode(db) != "manual_revision":
        return
    _close_open_segment(db, pharmacy_id, effective_date)
    db.add(
        orm.PharmacyPlanningRevisionSegment(
            pharmacy_id=pharmacy_id,
            valid_from=effective_date,
            valid_to=None,
            planning_weights_revision_id=MANUAL_PLANNING_WEIGHTS_REVISION_ID,
            planning_run_id=None,
            segment_source="manual",
            weights_override_from_request=False,
        )
    )


def find_segment_covering_visit(
    db: Session, pharmacy_id: uuid.UUID, visit_day: date
) -> orm.PharmacyPlanningRevisionSegment | None:
    q = (
        select(orm.PharmacyPlanningRevisionSegment)
        .where(
            orm.PharmacyPlanningRevisionSegment.pharmacy_id == pharmacy_id,
            orm.PharmacyPlanningRevisionSegment.valid_from <= visit_day,
            or_(
                orm.PharmacyPlanningRevisionSegment.valid_to.is_(None),
                visit_day < orm.PharmacyPlanningRevisionSegment.valid_to,
            ),
        )
        .order_by(desc(orm.PharmacyPlanningRevisionSegment.valid_from))
        .limit(1)
    )
    return db.execute(q).scalar_one_or_none()


def filter_visit_reports_for_planning_revision(
    db: Session,
    rows: list[orm.VisitReport],
    *,
    planning_weights_revision_id: uuid.UUID,
    pure_auto_planning_weights_only: bool,
) -> tuple[list[orm.VisitReport], dict[str, int]]:
    kept: list[orm.VisitReport] = []
    no_segment = 0
    revision_mismatch = 0
    filtered_out_override_or_manual = 0
    for r in rows:
        seg = find_segment_covering_visit(db, r.pharmacy_id, r.visit_date)
        if seg is None:
            no_segment += 1
            continue
        if seg.planning_weights_revision_id != planning_weights_revision_id:
            revision_mismatch += 1
            continue
        if pure_auto_planning_weights_only and (
            seg.segment_source != "auto" or seg.weights_override_from_request
        ):
            filtered_out_override_or_manual += 1
            continue
        kept.append(r)
    diag = {
        "excluded_no_segment": no_segment,
        "excluded_revision_mismatch": revision_mismatch,
        "excluded_manual_or_override_guard": filtered_out_override_or_manual,
    }
    return kept, diag
