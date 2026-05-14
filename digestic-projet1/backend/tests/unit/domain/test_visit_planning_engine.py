"""Tests unitaires — moteur planning (poids, entrées, assignation gloutonne)."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.visit_planning_engine import (
    PharmacyPlanningInputs,
    PlanningWeights,
    build_inputs_from_row,
    district_key,
    haversine_km,
    run_planning_assignment,
)


def test_planning_weights_merge_defaults_when_empty():
    w = PlanningWeights.merge(None)
    assert w.stock_out == 120.0
    assert w.visits_max_per_day == 14


def test_planning_weights_merge_partial_override_coerces_types():
    w = PlanningWeights.merge({"stock_out": 99.5, "visits_max_per_day": 8})
    assert w.stock_out == pytest.approx(99.5)
    assert w.visits_max_per_day == 8
    assert w.stock_low == 55.0


def test_planning_weights_merge_ignores_unknown_keys():
    w = PlanningWeights.merge({"unknown_field": 123, "geo_weight": 12.0})
    assert not hasattr(w, "unknown_field")
    assert w.geo_weight == pytest.approx(12.0)


def test_planning_weights_merge_none_value_skipped():
    """Une clé avec valeur None ne doit pas écraser le défaut."""
    w = PlanningWeights.merge({"stock_out": None, "geo_weight": 10.0})
    assert w.stock_out == pytest.approx(120.0)
    assert w.geo_weight == pytest.approx(10.0)


def test_district_key_truncates_postal_and_uppercases_city():
    assert district_key("06000", "nice") == "0600|NICE"


def test_haversine_same_point_zero():
    assert haversine_km(43.7, 7.26, 43.7, 7.26) == pytest.approx(0.0, abs=1e-9)


def test_build_inputs_from_row_parsing():
    pid = "ph-1"
    cid = "comm-1"
    inp = build_inputs_from_row(
        pharmacy_id=pid,
        commercial_id=cid,
        postal_code="06000",
        city="Nice",
        latitude=43.7,
        longitude=7.26,
        next_visit_date_raw="2026-05-01",
        planning_hard_rdv_raw=None,
        last_visit_raw=None,
        stock_status="LOW",
        visit_failed_reason="refus",
    )
    assert inp.id == pid
    assert inp.district == "0600|NICE"
    assert inp.stock_status == "low"
    assert inp.visit_failed_reason == "refus"
    assert inp.next_visit_date == date(2026, 5, 1)


def test_run_planning_hard_rdv_assigns_clamped_day():
    ref = date(2026, 5, 1)
    p = PharmacyPlanningInputs(
        id="a",
        commercial_id="c1",
        district="0600|NICE",
        latitude=None,
        longitude=None,
        next_visit_date=None,
        planning_hard_rdv_date=ref,
        last_visit_date=None,
        stock_status="good",
        visit_failed_reason=None,
    )
    res = run_planning_assignment([p], reference_date=ref, horizon_days=7, weights=PlanningWeights())
    assert res.assignments["a"] == ref


def test_run_planning_hard_rdv_outside_horizon_clamped_to_end():
    ref = date(2026, 5, 1)
    hard = date(2026, 6, 1)
    p = PharmacyPlanningInputs(
        id="a",
        commercial_id="c1",
        district="x",
        latitude=None,
        longitude=None,
        next_visit_date=None,
        planning_hard_rdv_date=hard,
        last_visit_date=None,
        stock_status="good",
        visit_failed_reason=None,
    )
    res = run_planning_assignment([p], reference_date=ref, horizon_days=7, weights=PlanningWeights())
    assert res.assignments["a"] == date(2026, 5, 7)


def test_run_planning_capacity_alert_when_hard_overflow():
    ref = date(2026, 5, 1)
    w = PlanningWeights(visits_max_per_day=1)
    rows = [
        PharmacyPlanningInputs(
            id=str(i),
            commercial_id="c1",
            district="d",
            latitude=None,
            longitude=None,
            next_visit_date=None,
            planning_hard_rdv_date=ref,
            last_visit_date=None,
            stock_status="good",
            visit_failed_reason=None,
        )
        for i in range(2)
    ]
    res = run_planning_assignment(rows, reference_date=ref, horizon_days=7, weights=w)
    assert res.assignments["0"] == ref
    assert res.assignments["1"] == ref
    assert "rdv_dur_capacity_depassee_assigne_quand_meme" in res.alerts.get("1", "")


def test_run_planning_skips_duplicate_ids():
    ref = date(2026, 5, 1)
    base_kw = dict(
        commercial_id="c1",
        district="d",
        latitude=None,
        longitude=None,
        next_visit_date=None,
        planning_hard_rdv_date=None,
        last_visit_date=None,
        visit_failed_reason=None,
    )
    p1 = PharmacyPlanningInputs(id="same", stock_status="good", **base_kw)
    p2 = PharmacyPlanningInputs(id="same", stock_status="low", **base_kw)
    res = run_planning_assignment([p1, p2], reference_date=ref, horizon_days=7, weights=PlanningWeights())
    assert list(res.assignments.keys()) == ["same"]
