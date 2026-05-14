"""Tests unitaires — formule note terrain v1."""
from __future__ import annotations

import pytest

from app.domain.planning_evaluation_v1 import (
    VERSION,
    FEELING_NEUTRAL_WHEN_MISSING,
    completion_subscore,
    composite_note,
    feeling_subscore_from_ratings,
    stock_subscore_from_statuses,
    build_breakdown,
)


def test_completion_subscore():
    assert completion_subscore(3, 4) == 75.0
    assert completion_subscore(0, 0) is None


def test_stock_subscore_average():
    assert stock_subscore_from_statuses(["good", "good", "low"]) == pytest.approx(
        (100 + 100 + 45) / 3, abs=0.02
    )


def test_feeling_subscore_neutral_flag():
    score, neutral = feeling_subscore_from_ratings([])
    assert score is None and neutral is True
    score2, neutral2 = feeling_subscore_from_ratings([5, 1])
    assert neutral2 is False
    assert score2 == pytest.approx(50.0)


def test_composite_matches_manual_example():
    """75 % réalisation, stock moyen 86.25, ressenti moyen 75."""
    c = composite_note(75.0, 86.25, 75.0)
    assert c == pytest.approx(78.9, rel=1e-3)


def test_composite_note_returns_none_if_completion_missing():
    assert composite_note(None, 80.0, 50.0) is None


def test_composite_note_returns_none_if_stock_missing():
    assert composite_note(80.0, None, 50.0) is None


def test_composite_note_uses_neutral_feeling_when_feeling_none():
    c = composite_note(100.0, 100.0, None)
    assert c == pytest.approx(
        0.35 * 100 + 0.35 * 100 + 0.30 * FEELING_NEUTRAL_WHEN_MISSING,
        abs=0.05,
    )


def test_build_breakdown_expected_keys():
    d = build_breakdown(
        completed_count=3,
        total_reports=4,
        stock_statuses=["good", "good", "low", "good"],
        feeling_ratings=[5, 4, 3],
    )
    assert d["version"] == VERSION
    assert d["composite_0_100"] == pytest.approx(78.9, rel=1e-2)
    assert d["subscores"]["feeling"]["neutral_assumption_used"] is False
