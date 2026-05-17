"""Tests unitaires — dernier dépôt par pharmacie pour la grille Planning."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Pharmacy, User, VisitReport, Warehouse
from app.repositories.visit_report_repository import VisitReportRepository
from app.services.visit_report_service import VisitReportService


@pytest.fixture
def planning_repo_session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    User.__table__.create(engine)
    Warehouse.__table__.create(engine)
    Pharmacy.__table__.create(engine)
    VisitReport.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    sess = maker()
    try:
        yield sess
    finally:
        sess.close()


def _seed_user_warehouse_pharmacy(sess: Session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    uid = uuid.uuid4()
    wid = uuid.uuid4()
    pid = uuid.uuid4()
    now = datetime.now()
    sess.add(
        User(
            id=uid,
            email=f"p-{uid.hex[:8]}@ut.local",
            password_hash="x",
            first_name="Comm",
            last_name="Ut",
            role="commercial",
            created_at=now,
            updated_at=now,
        )
    )
    sess.add(Warehouse(id=wid, name="Depot UT"))
    sess.add(
        Pharmacy(
            id=pid,
            name="Pharma UT",
            address_line="1 rue Test",
            city="Paris",
            postal_code="75001",
            country="FR",
            phone="0102030405",
            email=f"p-{pid.hex[:8]}@pharma.ut",
            warehouse_id=wid,
            commercial_id=uid,
        )
    )
    sess.commit()
    return uid, wid, pid


def _report(
    *,
    pharmacy_id: uuid.UUID,
    commercial_id: uuid.UUID,
    visit_date: date,
    has_deposit: bool,
    bottles_deposited: int,
) -> VisitReport:
    return VisitReport(
        id=uuid.uuid4(),
        visit_id=None,
        pharmacy_id=pharmacy_id,
        commercial_id=commercial_id,
        visit_date=visit_date,
        has_deposit=has_deposit,
        bottles_deposited=bottles_deposited,
    )


def test_find_latest_deposit_empty_pharmacy_ids(planning_repo_session):
    repo = VisitReportRepository(planning_repo_session)
    assert repo.find_latest_deposit_row_per_pharmacy([]) == []


def test_find_latest_deposit_no_qualifying_reports(planning_repo_session):
    sess = planning_repo_session
    uid, _, pid = _seed_user_warehouse_pharmacy(sess)
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 4, 1),
            has_deposit=False,
            bottles_deposited=5,
        )
    )
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 5, 1),
            has_deposit=True,
            bottles_deposited=0,
        )
    )
    sess.commit()
    repo = VisitReportRepository(sess)
    assert repo.find_latest_deposit_row_per_pharmacy([pid]) == []


def test_find_latest_deposit_picks_most_recent_eligible_visit(planning_repo_session):
    sess = planning_repo_session
    uid, _, pid = _seed_user_warehouse_pharmacy(sess)
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 3, 10),
            has_deposit=True,
            bottles_deposited=3,
        )
    )
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 5, 20),
            has_deposit=False,
            bottles_deposited=0,
        )
    )
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 5, 15),
            has_deposit=True,
            bottles_deposited=12,
        )
    )
    sess.commit()
    repo = VisitReportRepository(sess)
    rows = repo.find_latest_deposit_row_per_pharmacy([pid])
    assert len(rows) == 1
    pharmacy_id, visit_date, bottles = rows[0]
    assert pharmacy_id == pid
    assert visit_date == date(2026, 5, 15)
    assert bottles == 12


def test_find_latest_deposit_multiple_pharmacies(planning_repo_session):
    sess = planning_repo_session
    uid, wid, pid = _seed_user_warehouse_pharmacy(sess)
    p2 = uuid.uuid4()
    sess.add(
        Pharmacy(
            id=p2,
            name="Pharma 2",
            address_line="2 rue Test",
            city="Lyon",
            postal_code="69001",
            country="FR",
            phone="0203040506",
            email=f"p-{p2.hex[:8]}@pharma.ut",
            warehouse_id=wid,
            commercial_id=uid,
        )
    )
    sess.add(
        _report(
            pharmacy_id=p2,
            commercial_id=uid,
            visit_date=date(2026, 6, 1),
            has_deposit=True,
            bottles_deposited=7,
        )
    )
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 1, 1),
            has_deposit=True,
            bottles_deposited=1,
        )
    )
    sess.commit()
    repo = VisitReportRepository(sess)
    rows = repo.find_latest_deposit_row_per_pharmacy([pid, p2])
    by_pharmacy = {r[0]: (r[1], r[2]) for r in rows}
    assert by_pharmacy[pid][0] == date(2026, 1, 1) and by_pharmacy[pid][1] == 1
    assert by_pharmacy[p2][0] == date(2026, 6, 1) and by_pharmacy[p2][1] == 7


def test_service_get_last_deposits_skips_invalid_and_deduplicates(planning_repo_session):
    sess = planning_repo_session
    uid, _, pid = _seed_user_warehouse_pharmacy(sess)
    sess.add(
        _report(
            pharmacy_id=pid,
            commercial_id=uid,
            visit_date=date(2026, 2, 28),
            has_deposit=True,
            bottles_deposited=4,
        )
    )
    sess.commit()
    repo = VisitReportRepository(sess)
    svc = VisitReportService(sess, repo, MagicMock(), MagicMock(), MagicMock())
    raw_ids = ["not-a-uuid", str(pid), str(pid).upper()]
    items = svc.get_last_deposits_for_planning(raw_ids)
    assert len(items) == 1
    assert items[0]["pharmacy_id"] == str(pid)
    assert items[0]["visit_date"] == "2026-02-28"
    assert items[0]["bottles_deposited"] == 4


def test_service_get_last_deposits_truncates_to_max_ids(monkeypatch, planning_repo_session):
    """Les entrées au-delà de 1500 ne sont pas interrogées."""
    sess = planning_repo_session
    repo = VisitReportRepository(sess)
    svc = VisitReportService(sess, repo, MagicMock(), MagicMock(), MagicMock())

    captured: list[list[uuid.UUID]] = []

    def fake_find(ids: list[uuid.UUID]):
        captured.append(list(ids))
        return []

    monkeypatch.setattr(repo, "find_latest_deposit_row_per_pharmacy", fake_find)
    many = [str(uuid.uuid4()) for _ in range(1502)]
    svc.get_last_deposits_for_planning(many)
    assert len(captured) == 1
    assert len(captured[0]) == 1500
