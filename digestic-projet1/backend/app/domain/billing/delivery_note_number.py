"""Numérotation des bons de livraison Digestic (hors VosFactures)."""

from __future__ import annotations

import uuid
from datetime import date


def new_digestic_bl_number(*, for_date: date) -> str:
    """Ex. BL-20260428-A1B2C3D4 (jour de dépôt + suffixe unique)."""
    return f"BL-{for_date.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
