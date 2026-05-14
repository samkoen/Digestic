"""Jeux de données pour GET /api/planning/evaluation (tests d'intégration)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

import app.db.models as orm


def insert_visit_reports_for_evaluation_v1(
    db: Session,
    *,
    pharmacy_id: uuid.UUID,
    commercial_id: uuid.UUID,
    anchor_day: date,
) -> None:
    """
    Insère 4 rapports sur une même journée : prévisible pour assertions sur la note v1.

    - 3 « completed », 1 « not_completed » → réalisation 75 %
    - stocks : good, good, low, (ignored stock on not_completed still counted — we count ALL rows per service)
    Actually service counts ALL rows for stock average — include not_completed row stock_status too.

    Rows:
    1 completed good feeling 5 → feel contrib 100
    2 completed good feeling 4 → 75
    3 completed low feeling 3 → 50
    4 not_completed good feeling none

    Completion: 3/4 = 75
    Stock: (100+100+45+100)/4 = 86.25
    Feeling: ratings [5,4,3] → (100+75+50)/3 = 75
    Composite: 0.35*75 + 0.35*86.25 + 0.30*75 = 26.25 + 30.1875 + 22.5 = 78.9375 → 78.9
    """
    specs = [
        dict(
            visit_status="completed",
            stock_status="good",
            feeling=5,
        ),
        dict(
            visit_status="completed",
            stock_status="good",
            feeling=4,
        ),
        dict(
            visit_status="completed",
            stock_status="low",
            feeling=3,
        ),
        dict(
            visit_status="not_completed",
            stock_status="good",
            feeling=None,
            reason="pharmacy_closed",
        ),
    ]
    for sp in specs:
        db.add(
            orm.VisitReport(
                id=uuid.uuid4(),
                visit_id=None,
                pharmacy_id=pharmacy_id,
                commercial_id=commercial_id,
                visit_date=anchor_day,
                visit_status=sp["visit_status"],
                visit_not_completed_reason=sp.get("reason"),
                has_deposit=False,
                bottles_deposited=0,
                free_units=0,
                stock_status=sp["stock_status"],
                display_stand_status="unknown",
                covering_status="unknown",
                covering_size_to_order=None,
                next_visit_date=None,
                expected_return_iso_year=None,
                expected_return_iso_week=None,
                voice_note_url=None,
                photo_note_url=None,
                video_note_url=None,
                delivery_mode="normal",
                payment_mode="virement 30 jours",
                notes=None,
                feeling_rating=sp["feeling"],
                synced=False,
                billing_type="immediate",
                returns_quantity=0,
                bl_reduction_percent=0,
                return_source_visit_report_id=None,
            )
        )
    db.flush()
