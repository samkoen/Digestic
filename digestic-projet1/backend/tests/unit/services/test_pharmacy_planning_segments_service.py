"""Tests unitaires — segments révision planning par pharmacie."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

import app.db.models as orm
from app.planning_revision_constants import MANUAL_PLANNING_WEIGHTS_REVISION_ID
from app.services.pharmacy_planning_segments_service import (
    filter_visit_reports_for_planning_revision,
    get_manual_planning_segment_mode,
    maybe_record_manual_next_visit_segment,
    set_manual_planning_segment_mode,
    sync_segments_after_auto_planning_run,
)


def test_get_manual_planning_segment_mode_default_when_no_runtime_row():
    db = MagicMock()
    db.get.return_value = None
    assert get_manual_planning_segment_mode(db) == "inherit"


def test_get_manual_planning_segment_mode_invalid_fallback():
    db = MagicMock()
    rt = MagicMock()
    rt.manual_planning_segment_mode = "not_a_mode"
    db.get.return_value = rt
    assert get_manual_planning_segment_mode(db) == "inherit"


def test_get_manual_planning_segment_mode_manual_revision():
    db = MagicMock()
    rt = MagicMock()
    rt.manual_planning_segment_mode = "manual_revision"
    db.get.return_value = rt
    assert get_manual_planning_segment_mode(db) == "manual_revision"


def test_set_manual_planning_segment_mode_invalid_raises():
    db = MagicMock()
    with pytest.raises(ValueError, match="manual_planning_segment_mode invalide"):
        set_manual_planning_segment_mode(db, "oops")


def test_set_manual_planning_segment_mode_creates_singleton_when_missing():
    db = MagicMock()
    db.get.return_value = None
    set_manual_planning_segment_mode(db, "inherit", commit=False)
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, orm.PlanningRuntimeSettings)
    assert added.manual_planning_segment_mode == "inherit"


def test_sync_segments_after_auto_planning_run_close_then_add():
    db = MagicMock()
    pid = uuid.uuid4()
    baseline = uuid.uuid4()
    run_id = uuid.uuid4()
    segment_from = date(2026, 4, 10)

    sync_segments_after_auto_planning_run(
        db,
        pharmacy_ids=[pid],
        segment_valid_from=segment_from,
        planning_run_id=run_id,
        baseline_revision_id=baseline,
        weights_override_from_request=True,
    )

    db.execute.assert_called_once()
    db.add.assert_called_once()
    seg = db.add.call_args[0][0]
    assert isinstance(seg, orm.PharmacyPlanningRevisionSegment)
    assert seg.pharmacy_id == pid
    assert seg.valid_from == segment_from
    assert seg.valid_to is None
    assert seg.planning_weights_revision_id == baseline
    assert seg.planning_run_id == run_id
    assert seg.segment_source == "auto"
    assert seg.weights_override_from_request is True


def test_maybe_record_manual_segment_no_op_when_dates_unchanged():
    db = MagicMock()
    pid = uuid.uuid4()
    d = date(2026, 5, 1)
    maybe_record_manual_next_visit_segment(
        db,
        pharmacy_id=pid,
        previous_next_visit_date=d,
        new_next_visit_date=d,
        effective_date=date(2026, 5, 2),
    )
    db.execute.assert_not_called()
    db.add.assert_not_called()


def test_maybe_record_manual_segment_no_op_when_mode_inherit(monkeypatch):
    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.get_manual_planning_segment_mode",
        lambda _db: "inherit",
    )
    db = MagicMock()
    pid = uuid.uuid4()
    maybe_record_manual_next_visit_segment(
        db,
        pharmacy_id=pid,
        previous_next_visit_date=date(2026, 5, 1),
        new_next_visit_date=date(2026, 5, 8),
        effective_date=date(2026, 5, 2),
    )
    db.execute.assert_not_called()


def test_maybe_record_manual_segment_mode_b_writes_manual_revision(monkeypatch):
    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.get_manual_planning_segment_mode",
        lambda _db: "manual_revision",
    )
    db = MagicMock()
    pid = uuid.uuid4()
    eff = date(2026, 5, 3)
    maybe_record_manual_next_visit_segment(
        db,
        pharmacy_id=pid,
        previous_next_visit_date=date(2026, 5, 1),
        new_next_visit_date=date(2026, 5, 8),
        effective_date=eff,
    )
    db.execute.assert_called_once()
    db.add.assert_called_once()
    seg = db.add.call_args[0][0]
    assert seg.planning_weights_revision_id == MANUAL_PLANNING_WEIGHTS_REVISION_ID
    assert seg.segment_source == "manual"
    assert seg.valid_from == eff


def test_filter_visit_reports_keeps_pure_auto_matching_revision(monkeypatch):
    rev_target = uuid.uuid4()
    pid = uuid.uuid4()

    fake_seg = MagicMock()
    fake_seg.planning_weights_revision_id = rev_target
    fake_seg.segment_source = "auto"
    fake_seg.weights_override_from_request = False

    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, pharmacy_id, visit_day: fake_seg if pharmacy_id == pid else None,
    )

    db = MagicMock()
    r = MagicMock()
    r.pharmacy_id = pid
    r.visit_date = date(2026, 6, 1)

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=rev_target,
        pure_auto_planning_weights_only=True,
    )
    assert kept == [r]
    assert diag["excluded_no_segment"] == 0
    assert diag["excluded_revision_mismatch"] == 0
    assert diag["excluded_manual_or_override_guard"] == 0


def test_filter_visit_reports_excludes_when_pure_auto_and_manual_segment(monkeypatch):
    rev_target = uuid.uuid4()
    pid = uuid.uuid4()

    fake_seg = MagicMock()
    fake_seg.planning_weights_revision_id = rev_target
    fake_seg.segment_source = "manual"
    fake_seg.weights_override_from_request = False

    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, _pid, _vd: fake_seg,
    )

    db = MagicMock()
    r = MagicMock(pharmacy_id=pid, visit_date=date(2026, 6, 1))

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=rev_target,
        pure_auto_planning_weights_only=True,
    )
    assert kept == []
    assert diag["excluded_manual_or_override_guard"] == 1


def test_filter_visit_reports_excludes_revision_mismatch(monkeypatch):
    pid = uuid.uuid4()
    fake_seg = MagicMock()
    fake_seg.planning_weights_revision_id = uuid.uuid4()
    fake_seg.segment_source = "auto"
    fake_seg.weights_override_from_request = False

    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, _pid, _vd: fake_seg,
    )

    db = MagicMock()
    r = MagicMock(pharmacy_id=pid, visit_date=date(2026, 6, 1))
    wanted = uuid.uuid4()

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=wanted,
        pure_auto_planning_weights_only=True,
    )
    assert kept == []
    assert diag["excluded_revision_mismatch"] == 1


def test_filter_visit_reports_pure_auto_false_keeps_manual_same_revision(monkeypatch):
    rev_target = uuid.uuid4()
    pid = uuid.uuid4()

    fake_seg = MagicMock()
    fake_seg.planning_weights_revision_id = rev_target
    fake_seg.segment_source = "manual"
    fake_seg.weights_override_from_request = False

    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, _pid, _vd: fake_seg,
    )

    db = MagicMock()
    r = MagicMock(pharmacy_id=pid, visit_date=date(2026, 6, 1))

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=rev_target,
        pure_auto_planning_weights_only=False,
    )
    assert kept == [r]
    assert diag["excluded_manual_or_override_guard"] == 0


def test_filter_visit_reports_override_segment_excluded_under_pure_auto(monkeypatch):
    rev_target = uuid.uuid4()
    pid = uuid.uuid4()

    fake_seg = MagicMock()
    fake_seg.planning_weights_revision_id = rev_target
    fake_seg.segment_source = "auto"
    fake_seg.weights_override_from_request = True

    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, _pid, _vd: fake_seg,
    )

    db = MagicMock()
    r = MagicMock(pharmacy_id=pid, visit_date=date(2026, 6, 1))

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=rev_target,
        pure_auto_planning_weights_only=True,
    )
    assert kept == []
    assert diag["excluded_manual_or_override_guard"] == 1


def test_filter_visit_reports_counts_missing_segment(monkeypatch):
    monkeypatch.setattr(
        "app.services.pharmacy_planning_segments_service.find_segment_covering_visit",
        lambda _db, _pid, _vd: None,
    )
    db = MagicMock()
    r = MagicMock(pharmacy_id=uuid.uuid4(), visit_date=date(2026, 6, 1))

    kept, diag = filter_visit_reports_for_planning_revision(
        db,
        [r],
        planning_weights_revision_id=uuid.uuid4(),
        pure_auto_planning_weights_only=True,
    )
    assert kept == []
    assert diag["excluded_no_segment"] == 1
