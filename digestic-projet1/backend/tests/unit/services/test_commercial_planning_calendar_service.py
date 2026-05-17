"""Tests unitaires — calendrier planning commercial (repos récurrent + dates fermées)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import CommercialPlanningOffDate, CommercialPlanningOffWeekday, User
from app.services.commercial_planning_calendar_service import (
    commercial_has_planning_calendar_config,
    get_calendar_payload,
    get_working_dates_for_horizon,
    replace_commercial_calendar,
)


@pytest.fixture
def calendar_db_session() -> tuple[Session, uuid.UUID]:
    engine = create_engine("sqlite:///:memory:", future=True)
    User.__table__.create(engine)
    CommercialPlanningOffWeekday.__table__.create(engine)
    CommercialPlanningOffDate.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    sess = maker()
    uid = uuid.uuid4()
    now = datetime.now()
    sess.add(
        User(
            id=uid,
            email=f"cal-{uid.hex[:8]}@ut.local",
            password_hash="x",
            first_name="Cal",
            last_name="Ut",
            role="commercial",
            created_at=now,
            updated_at=now,
        )
    )
    sess.commit()
    try:
        yield sess, uid
    finally:
        sess.close()


def test_commercial_has_planning_calendar_config_false_when_empty(calendar_db_session):
    db, uid = calendar_db_session
    assert commercial_has_planning_calendar_config(db, uid) is False


def test_commercial_has_planning_calendar_config_true_with_weekday_rule(calendar_db_session):
    db, uid = calendar_db_session
    db.add(
        CommercialPlanningOffWeekday(commercial_user_id=uid, weekday=6),
    )
    db.commit()
    assert commercial_has_planning_calendar_config(db, uid) is True


def test_commercial_has_planning_calendar_config_true_with_off_date_only(calendar_db_session):
    db, uid = calendar_db_session
    db.add(
        CommercialPlanningOffDate(commercial_user_id=uid, off_date=date(2026, 5, 22), label=None),
    )
    db.commit()
    assert commercial_has_planning_calendar_config(db, uid) is True


def test_get_working_dates_returns_none_when_no_calendar_configured(calendar_db_session):
    db, uid = calendar_db_session
    ref = date(2026, 5, 18)
    assert (
        get_working_dates_for_horizon(db, commercial_user_id=uid, reference_date=ref, horizon_days=7)
        is None
    )


def test_get_working_dates_excludes_blocked_weekdays_python_convention(calendar_db_session):
    """5=samedi, 6=dimanche ; lun 18/05/2026 → ven 22 dans l’horizon 7 jours."""
    db, uid = calendar_db_session
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[5, 6],
        off_dates_payload=[],
    )
    db.commit()
    ref = date(2026, 5, 18)
    wd = get_working_dates_for_horizon(db, commercial_user_id=uid, reference_date=ref, horizon_days=7)
    assert wd is not None
    sat = date(2026, 5, 23)
    sun = date(2026, 5, 24)
    assert sat not in wd and sun not in wd
    assert ref in wd


def test_get_working_dates_excludes_off_date_within_horizon(calendar_db_session):
    db, uid = calendar_db_session
    conge = date(2026, 5, 22)
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[],
        off_dates_payload=[(conge, "Congés")],
    )
    db.commit()
    ref = date(2026, 5, 18)
    wd = get_working_dates_for_horizon(db, commercial_user_id=uid, reference_date=ref, horizon_days=10)
    assert wd is not None
    assert conge not in wd
    assert ref in wd


def test_get_working_dates_horizon_days_normalized_below_one(calendar_db_session):
    db, uid = calendar_db_session
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[5],
        off_dates_payload=[],
    )
    db.commit()
    ref = date(2026, 5, 22)
    wd = get_working_dates_for_horizon(db, commercial_user_id=uid, reference_date=ref, horizon_days=0)
    assert wd == frozenset({ref})


def test_get_calendar_payload_reflects_weekdays_and_dates_sorted(calendar_db_session):
    db, uid = calendar_db_session
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[6, 3, 5],
        off_dates_payload=[
            (date(2026, 7, 10), None),
            (date(2026, 6, 1), "Pont"),
        ],
    )
    db.commit()
    payload = get_calendar_payload(db, uid)
    assert payload["commercial_user_id"] == str(uid)
    assert payload["configured"] is True
    assert payload["off_weekdays"] == [3, 5, 6]
    assert len(payload["off_dates"]) == 2
    assert payload["off_dates"][0]["date"] == "2026-06-01"
    assert payload["off_dates"][0]["label"] == "Pont"
    assert payload["off_dates"][1]["date"] == "2026-07-10"


def test_replace_commercial_calendar_overwrites_previous_rules(calendar_db_session):
    db, uid = calendar_db_session
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[6],
        off_dates_payload=[(date(2026, 5, 1), None)],
    )
    db.commit()
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[5],
        off_dates_payload=[],
    )
    db.commit()
    rows_w = db.execute(
        select(CommercialPlanningOffWeekday).where(
            CommercialPlanningOffWeekday.commercial_user_id == uid,
        )
    ).scalars().all()
    rows_d = db.execute(
        select(CommercialPlanningOffDate).where(
            CommercialPlanningOffDate.commercial_user_id == uid,
        )
    ).scalars().all()
    assert [r.weekday for r in rows_w] == [5]
    assert rows_d == []


def test_replace_commercial_calendar_filters_invalid_weekday_indices(calendar_db_session):
    db, uid = calendar_db_session
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[-1, 99, 2, 2],
        off_dates_payload=[],
    )
    db.commit()
    rows = db.execute(
        select(CommercialPlanningOffWeekday).where(
            CommercialPlanningOffWeekday.commercial_user_id == uid,
        )
    ).scalars().all()
    assert [r.weekday for r in rows] == [2]


def test_replace_commercial_calendar_dedup_off_dates_prefers_labelled_payload(calendar_db_session):
    db, uid = calendar_db_session
    d = date(2026, 8, 15)
    replace_commercial_calendar(
        db,
        commercial_user_id=uid,
        off_weekdays=[],
        off_dates_payload=[
            (d, None),
            (d, "Formation"),
        ],
    )
    db.commit()
    row = db.execute(
        select(CommercialPlanningOffDate).where(
            CommercialPlanningOffDate.commercial_user_id == uid,
        )
    ).scalar_one()
    assert row.off_date == d
    assert row.label == "Formation"

