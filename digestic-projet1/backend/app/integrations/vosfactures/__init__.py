"""Intégration vosfactures.fr — mock + API."""

from app.integrations.vosfactures.factory import get_vosfactures_invoice_issuer
from app.integrations.vosfactures.http_client import VosFacturesApiClient
from app.integrations.vosfactures.mock_client import VosFacturesMockClient
from app.integrations.vosfactures.types import (
    VosFacturesCreditNoteResult,
    VosFacturesInvoiceResult,
)

__all__ = (
    "VosFacturesApiClient",
    "VosFacturesMockClient",
    "VosFacturesInvoiceResult",
    "VosFacturesCreditNoteResult",
    "get_vosfactures_invoice_issuer",
)
