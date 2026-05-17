"""Service : données SQL + orchestration planning par commercial."""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from collections.abc import Mapping
from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.domain.visit_planning_engine import (
    PlanningWeights,
    build_inputs_from_row,
    run_planning_assignment,
)
from app.services.commercial_planning_calendar_service import get_working_dates_for_horizon

logger = logging.getLogger(__name__)


class VisitPlanningService:
    """Recalcule les `next_visit_date` automatiquement (hors pharmacies en override manuel)."""

    NOTE_MANUAL_OVERRIDE = (
        "Pharmacies avec `planning_manual_override=true` sont ignorées. "
        "Repassez le flag à false sur la fiche pour réactiver le calcul auto."
    )

    def __init__(self, db: Session):
        self._db = db

    def _latest_visit_report_by_pharmacy(
        self, pharmacy_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, orm.VisitReport]:
        if not pharmacy_ids:
            return {}
        q = (
            select(orm.VisitReport)
            .where(orm.VisitReport.pharmacy_id.in_(pharmacy_ids))
            .order_by(orm.VisitReport.pharmacy_id, desc(orm.VisitReport.visit_date))
        )
        rows = self._db.execute(q).scalars().all()
        out: dict[uuid.UUID, orm.VisitReport] = {}
        for r in rows:
            if r.pharmacy_id not in out:
                out[r.pharmacy_id] = r
        return out

    def _manual_override_count(
        self,
        scope_commercial_uuids: list[uuid.UUID] | None,
        active_only: bool,
    ) -> int:
        qc = select(func.count()).select_from(orm.Pharmacy).where(
            orm.Pharmacy.planning_manual_override.is_(True),
            orm.Pharmacy.commercial_id.isnot(None),
        )
        if scope_commercial_uuids is not None:
            qc = qc.where(orm.Pharmacy.commercial_id.in_(scope_commercial_uuids))
        if active_only:
            qc = qc.where(orm.Pharmacy.pharmacy_status == "actif")
        return int(self._db.scalar(qc) or 0)

    def _snapshot_rows(
        self,
        scope_commercial_uuids: list[uuid.UUID] | None,
        active_only: bool,
    ):
        q = select(orm.Pharmacy).where(orm.Pharmacy.commercial_id.isnot(None))
        if scope_commercial_uuids is not None:
            q = q.where(orm.Pharmacy.commercial_id.in_(scope_commercial_uuids))
        if active_only:
            q = q.where(orm.Pharmacy.pharmacy_status == "actif")
        pharmacies = list(self._db.execute(q).scalars().all())
        pids = [p.id for p in pharmacies]
        reports = self._latest_visit_report_by_pharmacy(pids)

        snap = []
        for p in pharmacies:
            if getattr(p, "planning_manual_override", False):
                continue
            rep = reports.get(p.id)
            stk = getattr(rep, "stock_status", None) if rep else "unknown"
            fail_r = None
            if rep and (rep.visit_status or "") == "not_completed":
                fail_r = rep.visit_not_completed_reason
            snap.append(
                build_inputs_from_row(
                    pharmacy_id=str(p.id),
                    commercial_id=str(p.commercial_id),
                    postal_code=p.postal_code,
                    city=p.city,
                    latitude=p.latitude,
                    longitude=p.longitude,
                    next_visit_date_raw=p.next_visit_date,
                    planning_hard_rdv_raw=getattr(p, "planning_hard_rdv_date", None),
                    last_visit_raw=p.last_visit_at,
                    stock_status=stk,
                    visit_failed_reason=fail_r,
                )
            )
        return snap

    def run_planning(
        self,
        *,
        reference_date: date,
        horizon_days: int,
        scope_commercial_uuids: list[uuid.UUID] | None,
        weights_overrides: Mapping[str, object] | None,
        dry_run: bool,
        active_only: bool = True,
    ) -> dict:
        """`scope_commercial_uuids` ``None`` = tous les portefeuilles (pharmacies sans commercial exclues)."""

        weights = PlanningWeights.merge(dict(weights_overrides or {}))

        snapshots = self._snapshot_rows(scope_commercial_uuids, active_only)
        grouped: defaultdict[str, list] = defaultdict(list)
        for s in snapshots:
            grouped[s.commercial_id].append(s)

        merged_assignments: dict[str, date] = {}
        alerts: dict[str, str] = {}
        diagnostics: dict[str, object] = {}
        manual_skip_count = self._manual_override_count(scope_commercial_uuids, active_only)

        for comm_id_str, subset in grouped.items():
            try:
                comm_uuid = uuid.UUID(str(comm_id_str).strip())
            except ValueError:
                comm_uuid = None
            wd_set = None
            if comm_uuid is not None:
                wd_set = get_working_dates_for_horizon(
                    self._db,
                    commercial_user_id=comm_uuid,
                    reference_date=reference_date,
                    horizon_days=horizon_days,
                )
            result = run_planning_assignment(
                subset,
                reference_date,
                horizon_days,
                weights,
                working_dates=wd_set,
            )
            merged_assignments.update(result.assignments)
            alerts.update(result.alerts)
            diagnostics[comm_id_str] = result.diagnostics

        skipped_capacity_flex_ids: list[str] = []
        skipped_capacity_flex_count = 0
        for d in diagnostics.values():
            if not isinstance(d, dict):
                continue
            skipped_capacity_flex_count += int(d.get("skipped_capacity_flex_count") or 0)
            raw_ids = d.get("skipped_capacity_flex_ids")
            if isinstance(raw_ids, list):
                skipped_capacity_flex_ids.extend(str(x) for x in raw_ids)
        skipped_capacity_flex_ids.sort()

        details: list[dict] = []
        for pid, d in merged_assignments.items():
            entry: dict = {
                "pharmacy_id": pid,
                "next_visit_date": d.isoformat(),
            }
            if pid in alerts:
                entry["alert"] = alerts[pid]
            details.append(entry)

        if dry_run:
            return {
                "dry_run": True,
                "reference_date": reference_date.isoformat(),
                "horizon_days": horizon_days,
                "skipped_manual_override_count": manual_skip_count,
                "skipped_capacity_flex_count": skipped_capacity_flex_count,
                "skipped_capacity_flex_pharmacy_ids": skipped_capacity_flex_ids,
                "planned_count": len(merged_assignments),
                "assigned_pharmacy_ids": sorted(merged_assignments.keys()),
                "default_weights": PlanningWeights().__dict__,
                "applied_weights": weights.__dict__,
                "assignments_preview": sorted(details, key=lambda x: x["pharmacy_id"]),
                "per_commercial_day_load": diagnostics,
                "note": self.NOTE_MANUAL_OVERRIDE,
            }

        for pid, d in merged_assignments.items():
            row = self._db.get(orm.Pharmacy, uuid.UUID(pid))
            if row is not None and not getattr(row, "planning_manual_override", False):
                row.next_visit_date = d
        self._db.commit()

        try:
            from app.services.planning_rdv_hard_alert_notifications import (
                notify_planning_rdv_hard_alerts_maybe,
            )

            notify_planning_rdv_hard_alerts_maybe(
                self._db,
                alerts=alerts,
                assignments=merged_assignments,
                reference_date=reference_date,
                horizon_days=horizon_days,
            )
        except Exception:
            logger.exception(
                "Impossible d’envoyer les e-mails d’alerte RDV dur (le planning a bien été appliqué)."
            )

        return {
            "dry_run": False,
            "reference_date": reference_date.isoformat(),
            "horizon_days": horizon_days,
            "skipped_manual_override_count": manual_skip_count,
            "skipped_capacity_flex_count": skipped_capacity_flex_count,
            "skipped_capacity_flex_pharmacy_ids": skipped_capacity_flex_ids,
            "updated_count": len(merged_assignments),
            "assigned_pharmacy_ids": sorted(merged_assignments.keys()),
            "default_weights": PlanningWeights().__dict__,
            "applied_weights": weights.__dict__,
            "warnings": alerts,
            "note": self.NOTE_MANUAL_OVERRIDE,
        }
