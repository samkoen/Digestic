"""Tests unitaires : règles métier dépôt-vente (service, dépôt simulé)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models.delivery_note import DeliveryNote
from app.services.delivery_note_service import DeliveryNoteService


def _service_with_repo(note: DeliveryNote | None) -> DeliveryNoteService:
    repo = MagicMock()
    repo.find_by_id.return_value = note
    repo.update.return_value = note
    invoice_repo = MagicMock()
    pharm_repo = MagicMock()
    db = MagicMock(spec=Session)
    return DeliveryNoteService(repo, invoice_repo, pharm_repo, db)


def test_validate_depot_vente_requires_status():
    note = DeliveryNote(
        id="550e8400-e29b-41d4-a716-446655440000",
        pharmacy_id="660e8400-e29b-41d4-a716-446655440001",
        commercial_id="770e8400-e29b-41d4-a716-446655440002",
        delivery_date="2026-05-10",
        bottles_count=1,
        status="pending",
        is_deposit_sale=False,
    )
    svc = _service_with_repo(note)
    with pytest.raises(ValueError, match="dépôt-vente"):
        svc.validate_depot_vente_to_pending(note.id)


def test_validate_depot_vente_rejects_cancelled():
    note = DeliveryNote(
        id="550e8400-e29b-41d4-a716-446655440000",
        pharmacy_id="660e8400-e29b-41d4-a716-446655440001",
        commercial_id="770e8400-e29b-41d4-a716-446655440002",
        delivery_date="2026-05-10",
        bottles_count=1,
        status="cancelled",
        is_deposit_sale=True,
    )
    svc = _service_with_repo(note)
    with pytest.raises(ValueError, match="annulé"):
        svc.validate_depot_vente_to_pending(note.id)
