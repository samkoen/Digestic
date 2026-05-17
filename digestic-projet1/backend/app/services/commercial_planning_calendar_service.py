"""Calendrier de travail pour le planning auto : journées fermées récurrentes + dates ponctuelles."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

import app.db.models as orm


def commercial_has_planning_calendar_config(db: Session, commercial_user_id: uuid.UUID) -> bool:
    nw = db.scalar(
        select(func.count())
        .select_from(orm.CommercialPlanningOffWeekday)
        .where(orm.CommercialPlanningOffWeekday.commercial_user_id == commercial_user_id)
    )
    nd = db.scalar(
        select(func.count())
        .select_from(orm.CommercialPlanningOffDate)
        .where(orm.CommercialPlanningOffDate.commercial_user_id == commercial_user_id)
    )
    return int(nw or 0) > 0 or int(nd or 0) > 0


def get_working_dates_for_horizon(
    db: Session,
    *,
    commercial_user_id: uuid.UUID,
    reference_date: date,
    horizon_days: int,
) -> frozenset[date] | None:
    """
    Sous-ensemble des jours civils [reference_date, reference_date + horizon_days) où le commercial peut
    recevoir une visite en planning auto.

    Retourne ``None`` s’aucune règle n’est configurée (= comportement historique : **tous** les jours).
    """
    if horizon_days < 1:
        horizon_days = 1
    horizon: list[date] = [
        reference_date + timedelta(days=i) for i in range(horizon_days)
    ]

    if not commercial_has_planning_calendar_config(db, commercial_user_id):
        return None

    wd_rows = db.execute(
        select(orm.CommercialPlanningOffWeekday.weekday).where(
            orm.CommercialPlanningOffWeekday.commercial_user_id == commercial_user_id
        )
    ).scalars().all()
    off_weekdays = {int(w) for w in wd_rows}

    end_excl = reference_date + timedelta(days=horizon_days)
    date_rows = db.execute(
        select(orm.CommercialPlanningOffDate.off_date).where(
            orm.CommercialPlanningOffDate.commercial_user_id == commercial_user_id,
            orm.CommercialPlanningOffDate.off_date >= reference_date,
            orm.CommercialPlanningOffDate.off_date < end_excl,
        )
    ).scalars().all()
    off_dates = {d for d in date_rows}

    out: list[date] = []
    for d in horizon:
        if int(d.weekday()) in off_weekdays:
            continue
        if d in off_dates:
            continue
        out.append(d)
    return frozenset(out)


def get_calendar_payload(db: Session, commercial_user_id: uuid.UUID) -> dict:
    weekdays = sorted(
        int(w)
        for w in db.execute(
            select(orm.CommercialPlanningOffWeekday.weekday).where(
                orm.CommercialPlanningOffWeekday.commercial_user_id == commercial_user_id
            )
        ).scalars().all()
    )
    date_rows = db.execute(
        select(orm.CommercialPlanningOffDate)
        .where(orm.CommercialPlanningOffDate.commercial_user_id == commercial_user_id)
        .order_by(orm.CommercialPlanningOffDate.off_date)
    ).scalars().all()
    return {
        "commercial_user_id": str(commercial_user_id),
        "off_weekdays": weekdays,
        "off_dates": [
            {"date": r.off_date.isoformat(), "label": r.label} for r in date_rows
        ],
        "configured": commercial_has_planning_calendar_config(db, commercial_user_id),
    }


def replace_commercial_calendar(
    db: Session,
    *,
    commercial_user_id: uuid.UUID,
    off_weekdays: list[int],
    off_dates_payload: list[tuple[date, str | None]],
) -> None:
    """Remplace tout le calendrier du commercial en une transaction."""
    uw = sorted({int(x) for x in off_weekdays if 0 <= int(x) <= 6})

    uniq_dates: dict[date, str | None] = {}
    for d, lab in off_dates_payload:
        if d not in uniq_dates or (lab or "").strip():
            uniq_dates[d] = (lab or "").strip() or None

    db.execute(
        delete(orm.CommercialPlanningOffWeekday).where(
            orm.CommercialPlanningOffWeekday.commercial_user_id == commercial_user_id
        )
    )
    db.execute(
        delete(orm.CommercialPlanningOffDate).where(
            orm.CommercialPlanningOffDate.commercial_user_id == commercial_user_id
        )
    )

    for w in uw:
        db.add(
            orm.CommercialPlanningOffWeekday(
                commercial_user_id=commercial_user_id,
                weekday=w,
            )
        )
    for d, lbl in sorted(uniq_dates.items(), key=lambda x: x[0]):
        db.add(
            orm.CommercialPlanningOffDate(
                commercial_user_id=commercial_user_id,
                off_date=d,
                label=lbl,
            )
        )
