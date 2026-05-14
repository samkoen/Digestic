"""Agrégation SQL des rapports de visite pour la note terrain v1."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.domain.planning_evaluation_v1 import (
    FORMULA_DOCUMENTATION_FR,
    VERSION,
    build_breakdown,
)
from app.services.pharmacy_planning_segments_service import filter_visit_reports_for_planning_revision


class PlanningEvaluationService:
    def evaluate_period(
        self,
        db: Session,
        *,
        start: date,
        end: date,
        commercial_id: uuid.UUID | None,
        planning_weights_revision_id: uuid.UUID | None = None,
        pure_auto_planning_weights_only: bool = True,
    ) -> dict:
        q: Select[tuple[orm.VisitReport]] = select(orm.VisitReport).where(
            orm.VisitReport.visit_date >= start,
            orm.VisitReport.visit_date <= end,
        )
        if commercial_id is not None:
            q = q.where(orm.VisitReport.commercial_id == commercial_id)

        rows = list(db.execute(q).scalars().all())

        revision_filter_meta: dict | None = None
        if planning_weights_revision_id is not None:
            before_ct = len(rows)
            rows, diag = filter_visit_reports_for_planning_revision(
                db,
                rows,
                planning_weights_revision_id=planning_weights_revision_id,
                pure_auto_planning_weights_only=pure_auto_planning_weights_only,
            )
            revision_filter_meta = {
                "planning_weights_revision_id": str(planning_weights_revision_id),
                "pure_auto_planning_weights_only": pure_auto_planning_weights_only,
                "reports_before_filter": before_ct,
                "reports_after_filter": len(rows),
                **diag,
            }

        total = len(rows)
        if total == 0:
            empty = {
                "version": VERSION,
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "commercial_id": str(commercial_id) if commercial_id else None,
                "report_count": 0,
                "composite_0_100": None,
                "subscores": None,
                "counts": None,
                "formula_documentation_fr": FORMULA_DOCUMENTATION_FR,
                "message_fr": "Aucun rapport de visite sur cette période (filtres inclus).",
            }
            if revision_filter_meta:
                empty["planning_revision_filter"] = revision_filter_meta
            return empty

        completed = sum(1 for r in rows if (r.visit_status or "").strip() == "completed")
        stock_statuses = [r.stock_status for r in rows]
        ratings: list[int] = []
        for r in rows:
            fr = getattr(r, "feeling_rating", None)
            if fr is not None:
                try:
                    ratings.append(int(fr))
                except (TypeError, ValueError):
                    pass

        breakdown = build_breakdown(
            completed_count=completed,
            total_reports=total,
            stock_statuses=stock_statuses,
            feeling_ratings=ratings,
        )

        out = {
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "commercial_id": str(commercial_id) if commercial_id else None,
            **breakdown,
            "message_fr": None,
        }
        if revision_filter_meta:
            out["planning_revision_filter"] = revision_filter_meta
        return out

