"""Constantes pour les révisions planning (sentinel « manuel », etc.)."""

from __future__ import annotations

import uuid

# Révision sentinel Mode B — même UUID que dans la migration Alembic z8a9.
MANUAL_PLANNING_WEIGHTS_REVISION_ID: uuid.UUID = uuid.UUID(
    "00000000-0000-4000-8000-000000000001"
)
MANUAL_PLANNING_WEIGHTS_REVISION_NUMBER: int = 0
