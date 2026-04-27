"""Délai de paiement (échéance) déduit du libellé mode de paiement."""

from __future__ import annotations

from datetime import date, timedelta


def payment_delay_days(payment_mode: str | None) -> int:
    if not payment_mode:
        return 30
    s = " ".join(
        str(payment_mode).lower().replace("_", " ").replace("-", " ").split()
    )
    if "60" in s:
        return 60
    return 30


def due_date_for_invoice(issue_date: date, payment_mode: str | None) -> date:
    return issue_date + timedelta(days=payment_delay_days(payment_mode))
