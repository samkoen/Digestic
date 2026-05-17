import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.visit_report import VisitReport


class VisitReportRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[VisitReport]:
        rows = self._db.execute(select(orm.VisitReport)).scalars().all()
        return [mp.report_orm_to_domain(r) for r in rows]

    def find_latest_deposit_row_per_pharmacy(
        self, pharmacy_ids: list[uuid.UUID]
    ) -> list[tuple[uuid.UUID, object, int]]:
        """Pour chaque pharmacie : ligne la plus récente avec dépôt (has_deposit et bouteilles > 0)."""
        if not pharmacy_ids:
            return []
        rn = (
            func.row_number()
            .over(
                partition_by=orm.VisitReport.pharmacy_id,
                order_by=orm.VisitReport.visit_date.desc(),
            )
            .label("rn")
        )
        subq = (
            select(
                orm.VisitReport.pharmacy_id,
                orm.VisitReport.visit_date,
                orm.VisitReport.bottles_deposited,
                rn,
            )
            .where(
                orm.VisitReport.pharmacy_id.in_(pharmacy_ids),
                orm.VisitReport.has_deposit.is_(True),
                orm.VisitReport.bottles_deposited > 0,
            )
            .subquery()
        )
        stmt = select(
            subq.c.pharmacy_id,
            subq.c.visit_date,
            subq.c.bottles_deposited,
        ).where(subq.c.rn == 1)
        rows = self._db.execute(stmt).all()
        return [(r[0], r[1], int(r[2] or 0)) for r in rows]

    def find_by_id(self, id_: str) -> Optional[VisitReport]:
        try:
            rid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.VisitReport, rid)
        return mp.report_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[VisitReport]:
        q = select(orm.VisitReport)
        for k, v in kwargs.items():
            if k in ("pharmacy_id", "commercial_id", "visit_id") and v is not None:
                v = mp.parse_uuid(v)
            q = q.where(getattr(orm.VisitReport, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.report_orm_to_domain(r) for r in rows]

    def find_by_commercial(self, commercial_id: str) -> list[VisitReport]:
        return self.find_by(commercial_id=commercial_id)

    def find_by_pharmacy(self, pharmacy_id: str) -> list[VisitReport]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def find_unsynced(self) -> list[VisitReport]:
        q = select(orm.VisitReport).where(orm.VisitReport.synced.is_(False))
        rows = self._db.execute(q).scalars().all()
        return [mp.report_orm_to_domain(r) for r in rows]

    def create(self, model: VisitReport) -> VisitReport:
        nvd = mp.parse_date(model.next_visit_date) if model.next_visit_date else None
        _vid = (getattr(model, "visit_id", None) or "").strip()
        row = orm.VisitReport(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            visit_id=mp.parse_uuid(_vid) if _vid else None,
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            commercial_id=mp.parse_uuid(model.commercial_id),
            visit_date=mp.parse_date(model.visit_date),
            visit_status=model.visit_status,
            visit_not_completed_reason=model.visit_not_completed_reason,
            has_deposit=model.has_deposit,
            bottles_deposited=model.bottles_deposited,
            free_units=model.free_units,
            stock_status=model.stock_status,
            display_stand_status=model.display_stand_status,
            covering_status=model.covering_status,
            covering_size_to_order=model.covering_size_to_order,
            next_visit_date=nvd,
            expected_return_iso_year=model.expected_return_iso_year,
            expected_return_iso_week=model.expected_return_iso_week,
            voice_note_url=model.voice_note_url,
            photo_note_url=model.photo_note_url,
            video_note_url=model.video_note_url,
            delivery_mode=model.delivery_mode,
            payment_mode=mp.normalize_payment_mode_to_db(model.payment_mode),
            notes=model.notes,
            feeling_rating=getattr(model, "feeling_rating", None),
            synced=model.synced,
            billing_type=model.billing_type or "immediate",
            returns_quantity=int(getattr(model, "returns_quantity", 0) or 0),
            return_source_visit_report_id=(
                mp.parse_uuid(model.return_source_visit_report_id)
                if getattr(model, "return_source_visit_report_id", None)
                else None
            ),
            bl_reduction_percent=float(getattr(model, "bl_reduction", 0) or 0),
        )
        self._db.add(row)
        self._db.flush()
        return mp.report_orm_to_domain(row)

    def update(self, id_: str, model: VisitReport) -> Optional[VisitReport]:
        try:
            rid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.VisitReport, rid)
        if not row:
            return None
        if model.visit_id:
            row.visit_id = mp.parse_uuid(model.visit_id)
        row.pharmacy_id = mp.parse_uuid(model.pharmacy_id)
        row.commercial_id = mp.parse_uuid(model.commercial_id)
        row.visit_date = mp.parse_date(model.visit_date)
        row.visit_status = model.visit_status
        row.visit_not_completed_reason = model.visit_not_completed_reason
        row.has_deposit = model.has_deposit
        row.bottles_deposited = model.bottles_deposited
        row.free_units = model.free_units
        row.stock_status = model.stock_status
        row.display_stand_status = model.display_stand_status
        row.covering_status = model.covering_status
        row.covering_size_to_order = model.covering_size_to_order
        row.next_visit_date = (
            mp.parse_date(model.next_visit_date) if model.next_visit_date else None
        )
        row.expected_return_iso_year = model.expected_return_iso_year
        row.expected_return_iso_week = model.expected_return_iso_week
        row.voice_note_url = model.voice_note_url
        row.photo_note_url = model.photo_note_url
        row.video_note_url = model.video_note_url
        row.delivery_mode = model.delivery_mode
        row.payment_mode = mp.normalize_payment_mode_to_db(model.payment_mode)
        row.notes = model.notes
        row.synced = model.synced
        if hasattr(model, "billing_type"):
            row.billing_type = model.billing_type or "immediate"
        if hasattr(model, "returns_quantity"):
            row.returns_quantity = int(model.returns_quantity or 0)
        if hasattr(model, "return_source_visit_report_id"):
            row.return_source_visit_report_id = (
                mp.parse_uuid(model.return_source_visit_report_id)
                if model.return_source_visit_report_id
                else None
            )
        if hasattr(model, "bl_reduction"):
            row.bl_reduction_percent = float(model.bl_reduction or 0)
        if hasattr(model, "feeling_rating"):
            row.feeling_rating = getattr(model, "feeling_rating", None)
        self._db.flush()
        return mp.report_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            rid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.VisitReport, rid)
        if not row:
            return False
        self._db.delete(row)
        return True
