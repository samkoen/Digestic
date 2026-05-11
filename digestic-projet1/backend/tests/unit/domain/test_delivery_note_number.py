"""Tests unitaires : numérotation des BL."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

from app.domain.billing.delivery_note_number import new_digestic_bl_number


def test_new_digestic_bl_number_format():
    fixed = uuid.UUID("12345678-9abc-4def-a234-567812345678")

    with patch(
        "app.domain.billing.delivery_note_number.uuid.uuid4",
        return_value=fixed,
    ):
        num = new_digestic_bl_number(for_date=date(2026, 5, 10))

    assert num == f"BL-20260510-{fixed.hex[:8].upper()}"
