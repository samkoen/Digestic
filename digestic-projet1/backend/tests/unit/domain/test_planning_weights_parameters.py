"""Tests unitaires — tous les paramètres ``PlanningWeights`` (fusion / snapshot API)."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from app.domain.visit_planning_engine import (
    PharmacyPlanningInputs,
    PlanningWeights,
    run_planning_assignment,
)
from app.services.planning_weights_config_service import normalize_weights_payload


def test_planning_weights_dataclass_fields_cover_expected_parameters():
    """Liste figée des clés métier ; à ajuster si un nouveau paramètre est introduit."""
    names = {f.name for f in fields(PlanningWeights)}
    expected = {
        "stock_out",
        "stock_low",
        "failed_closed",
        "failed_other",
        "per_day_overdue",
        "max_overdue_bonus",
        "in_target_week",
        "geo_weight",
        "fill_radius_km",
        "district_density",
        "visits_max_per_day",
        "default_cycle_days",
        "orphan_horizon_bonus_days",
    }
    assert names == expected


def test_planning_weights_merge_none_matches_literal_defaults():
    w = PlanningWeights.merge(None)
    assert w.stock_out == pytest.approx(120.0)
    assert w.stock_low == pytest.approx(55.0)
    assert w.failed_closed == pytest.approx(48.0)
    assert w.failed_other == pytest.approx(22.0)
    assert w.per_day_overdue == pytest.approx(10.0)
    assert w.max_overdue_bonus == pytest.approx(90.0)
    assert w.in_target_week == pytest.approx(72.0)
    assert w.geo_weight == pytest.approx(8.0)
    assert w.fill_radius_km == pytest.approx(14.0)
    assert w.district_density == pytest.approx(6.0)
    assert w.visits_max_per_day == 14
    assert w.default_cycle_days == 28
    assert w.orphan_horizon_bonus_days == 10


def test_planning_weights_merge_empty_dict_same_as_none():
    assert PlanningWeights.merge({}).__dict__ == PlanningWeights.merge(None).__dict__


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("stock_out", 111.5),
        ("stock_low", 44.25),
        ("failed_closed", 33.0),
        ("failed_other", 21.125),
        ("per_day_overdue", 12.5),
        ("max_overdue_bonus", 95.0),
        ("in_target_week", 68.0),
        ("geo_weight", 15.0),
        ("fill_radius_km", 22.5),
        ("district_density", 9.25),
        ("visits_max_per_day", 25),
        ("default_cycle_days", 21),
        ("orphan_horizon_bonus_days", 7),
    ],
)
def test_planning_weights_merge_single_override_preserves_other_defaults(field_name: str, value: float | int):
    w = PlanningWeights.merge({field_name: value})
    base = PlanningWeights.merge(None)
    if isinstance(value, float):
        assert getattr(w, field_name) == pytest.approx(value)
    else:
        assert getattr(w, field_name) == value
    for f in fields(PlanningWeights):
        if f.name != field_name:
            assert getattr(w, f.name) == getattr(base, f.name), f.name


def test_planning_weights_merge_full_override_all_parameters():
    merged = PlanningWeights.merge(
        {
            "stock_out": 1.0,
            "stock_low": 2.0,
            "failed_closed": 3.0,
            "failed_other": 4.0,
            "per_day_overdue": 5.0,
            "max_overdue_bonus": 6.0,
            "in_target_week": 7.0,
            "geo_weight": 8.5,
            "fill_radius_km": 9.5,
            "district_density": 10.5,
            "visits_max_per_day": 11,
            "default_cycle_days": 30,
            "orphan_horizon_bonus_days": 5,
        }
    )
    assert merged.stock_out == pytest.approx(1.0)
    assert merged.stock_low == pytest.approx(2.0)
    assert merged.failed_closed == pytest.approx(3.0)
    assert merged.failed_other == pytest.approx(4.0)
    assert merged.per_day_overdue == pytest.approx(5.0)
    assert merged.max_overdue_bonus == pytest.approx(6.0)
    assert merged.in_target_week == pytest.approx(7.0)
    assert merged.geo_weight == pytest.approx(8.5)
    assert merged.fill_radius_km == pytest.approx(9.5)
    assert merged.district_density == pytest.approx(10.5)
    assert merged.visits_max_per_day == 11
    assert merged.default_cycle_days == 30
    assert merged.orphan_horizon_bonus_days == 5


def test_planning_weights_merge_none_values_keep_defaults():
    w = PlanningWeights.merge(
        {
            "stock_out": None,
            "stock_low": None,
            "visits_max_per_day": None,
            "geo_weight": 99.0,
        }
    )
    base = PlanningWeights.merge(None)
    assert w.stock_out == pytest.approx(base.stock_out)
    assert w.stock_low == pytest.approx(base.stock_low)
    assert w.visits_max_per_day == base.visits_max_per_day
    assert w.geo_weight == pytest.approx(99.0)


def test_planning_weights_merge_coerces_numeric_strings():
    w = PlanningWeights.merge({"geo_weight": "12.25", "visits_max_per_day": "9"})
    assert w.geo_weight == pytest.approx(12.25)
    assert w.visits_max_per_day == 9


def test_planning_weights_merge_truncates_float_to_int_parameters():
    w = PlanningWeights.merge({"visits_max_per_day": 14.9, "default_cycle_days": 27.6})
    assert w.visits_max_per_day == 14
    assert w.default_cycle_days == 27


def test_planning_weights_merge_invalid_string_raises():
    with pytest.raises(ValueError):
        PlanningWeights.merge({"visits_max_per_day": "douze"})
    with pytest.raises(ValueError):
        PlanningWeights.merge({"geo_weight": "pas_un_nombre"})


def test_normalize_weights_payload_none_returns_full_defaults_matching_merge():
    snap = normalize_weights_payload(None)
    ref = PlanningWeights.merge(None).__dict__.copy()
    assert snap.keys() == ref.keys()
    for k in ref:
        if isinstance(ref[k], float):
            assert snap[k] == pytest.approx(ref[k])
        else:
            assert snap[k] == ref[k]


def test_normalize_weights_payload_partial_fill_remaining_defaults():
    snap = normalize_weights_payload({"district_density": 2.5, "default_cycle_days": 42})
    assert snap["district_density"] == pytest.approx(2.5)
    assert snap["default_cycle_days"] == 42
    assert snap["stock_out"] == pytest.approx(120.0)
    assert snap["visits_max_per_day"] == 14


def test_visits_max_per_day_controls_daily_capacity_in_engine():
    """Contrôle métier minimal sur la capacité journalière (paramètre critique)."""
    ref = date(2026, 9, 1)
    cap = 5
    w = PlanningWeights(visits_max_per_day=cap)
    rows = [
        PharmacyPlanningInputs(
            id=str(i),
            commercial_id="c1",
            district="d",
            latitude=None,
            longitude=None,
            next_visit_date=None,
            planning_hard_rdv_date=None,
            last_visit_date=None,
            stock_status="good",
            visit_failed_reason=None,
        )
        for i in range(12)
    ]
    res = run_planning_assignment(rows, reference_date=ref, horizon_days=7, weights=w)
    assert max(int(v) for v in res.diagnostics["day_load"].values()) <= cap
