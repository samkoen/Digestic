"""Tests unitaires — fusion révisions / snapshots poids planning."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.domain.visit_planning_engine import PlanningWeights
from app.services.planning_weights_config_service import (
    build_combined_weights_mapping,
    effective_weights_snapshot,
    normalize_weights_payload,
    set_active_revision_id,
)


def test_normalize_weights_payload_aligns_on_planning_weights_keys():
    snap = normalize_weights_payload({"geo_weight": 15})
    assert snap["geo_weight"] == pytest.approx(15.0)
    assert snap["stock_out"] == pytest.approx(PlanningWeights().stock_out)


def test_build_combined_weights_mapping_request_overrides_active(monkeypatch):
    rev_id = uuid.uuid4()
    rev = MagicMock()
    rev.id = rev_id
    rev.weights = {"stock_out": 80.0, "geo_weight": 10.0}

    monkeypatch.setattr(
        "app.services.planning_weights_config_service.get_active_revision",
        lambda _db: rev,
    )

    flat, aid, req = build_combined_weights_mapping(MagicMock(), {"geo_weight": 22.0})
    assert aid == rev_id
    assert flat["stock_out"] == pytest.approx(80.0)
    assert flat["geo_weight"] == pytest.approx(22.0)
    assert req == {"geo_weight": 22.0}


def test_build_combined_weights_mapping_no_active_only_request(monkeypatch):
    monkeypatch.setattr(
        "app.services.planning_weights_config_service.get_active_revision",
        lambda _db: None,
    )

    flat, aid, req = build_combined_weights_mapping(MagicMock(), {"visits_max_per_day": 9})
    assert aid is None
    assert flat["visits_max_per_day"] == 9


def test_build_combined_weights_mapping_active_without_weights_dict(monkeypatch):
    rev_id = uuid.uuid4()
    rev = MagicMock()
    rev.id = rev_id
    rev.weights = None

    monkeypatch.setattr(
        "app.services.planning_weights_config_service.get_active_revision",
        lambda _db: rev,
    )

    flat, aid, _req = build_combined_weights_mapping(MagicMock(), {"stock_low": 40.0})
    assert aid == rev_id
    assert flat["stock_low"] == pytest.approx(40.0)


def test_effective_weights_snapshot_from_active_revision(monkeypatch):
    rev = MagicMock()
    rev.weights = {"stock_out": 100.0}

    monkeypatch.setattr(
        "app.services.planning_weights_config_service.get_active_revision",
        lambda _db: rev,
    )

    snap = effective_weights_snapshot(MagicMock())
    assert snap["stock_out"] == pytest.approx(100.0)


def test_effective_weights_snapshot_fallback_defaults(monkeypatch):
    monkeypatch.setattr(
        "app.services.planning_weights_config_service.get_active_revision",
        lambda _db: None,
    )

    snap = effective_weights_snapshot(MagicMock())
    assert snap == PlanningWeights.merge(None).__dict__.copy()


def test_set_active_revision_id_raises_when_revision_missing():
    db = MagicMock()
    db.get.return_value = None

    missing_id = uuid.uuid4()
    with pytest.raises(ValueError, match="introuvable"):
        set_active_revision_id(db, missing_id, commit=False)


def test_set_active_revision_id_updates_existing_runtime():
    import app.db.models as orm_mod

    rev_id = uuid.uuid4()
    rev_row = MagicMock()
    rt = MagicMock()

    db = MagicMock()

    def get_side_effect(model, rid):
        if model is orm_mod.PlanningWeightsRevision and rid == rev_id:
            return rev_row
        if model is orm_mod.PlanningRuntimeSettings and rid == 1:
            return rt
        return None

    db.get.side_effect = get_side_effect

    set_active_revision_id(db, rev_id, commit=False)
    assert rt.active_revision_id == rev_id


def test_set_active_revision_id_inserts_runtime_when_absent():
    import app.db.models as orm_mod

    rev_id = uuid.uuid4()
    rev_row = MagicMock()

    db = MagicMock()

    def get_side_effect(model, rid):
        if model is orm_mod.PlanningWeightsRevision and rid == rev_id:
            return rev_row
        if model is orm_mod.PlanningRuntimeSettings and rid == 1:
            return None
        return None

    db.get.side_effect = get_side_effect

    set_active_revision_id(db, rev_id, commit=False)
    db.add.assert_called_once()
    added = db.add.call_args[0][0]
    assert isinstance(added, orm_mod.PlanningRuntimeSettings)
    assert added.active_revision_id == rev_id
