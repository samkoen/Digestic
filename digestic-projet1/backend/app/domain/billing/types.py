from __future__ import annotations

BILLING_IMMEDIATE = "immediate"
BILLING_MONTHLY_RECAP = "monthly_recap"


def normalize_billing_type(raw: str | None) -> str:
    if not raw or not str(raw).strip():
        return BILLING_IMMEDIATE
    s = str(raw).strip().lower()
    if s in ("recap", "recapitulative", "monthly", "monthly_recap", "fin_de_mois"):
        return BILLING_MONTHLY_RECAP
    if s in ("immediate", "immediat", "direct"):
        return BILLING_IMMEDIATE
    return BILLING_IMMEDIATE
