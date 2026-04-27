"""Types communs intégration factures (mock + API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class VosFacturesInvoiceResult:
    """Résultat d'émission (mock ou VosFactures)."""

    provider: str
    external_id: str | None
    invoice_number: str | None
    payload: dict[str, Any]
