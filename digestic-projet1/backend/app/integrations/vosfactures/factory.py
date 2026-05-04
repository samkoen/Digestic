"""Choisit le client facture : API réelle si configurée, sinon mock."""

from __future__ import annotations

from typing import Any, Protocol

from app.integrations.vosfactures.config import vosfactures_is_configured
from app.integrations.vosfactures.http_client import VosFacturesApiClient
from app.integrations.vosfactures.mock_client import VosFacturesMockClient
from app.integrations.vosfactures.types import (
    VosFacturesCreditNoteResult,
    VosFacturesInvoiceResult,
)


class VosFacturesInvoiceIssuer(Protocol):
    def issue_vat_invoice(self, **kwargs) -> VosFacturesInvoiceResult: ...

    def issue_total_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
    ) -> VosFacturesCreditNoteResult: ...

    def issue_partial_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
        positions: list[Any],
        lang: str,
    ) -> VosFacturesCreditNoteResult: ...


def get_vosfactures_invoice_issuer() -> VosFacturesInvoiceIssuer:
    if vosfactures_is_configured():
        return VosFacturesApiClient()
    return VosFacturesMockClient()
