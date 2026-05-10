"""Configuration Brevo (Sendinblue) — clé API et expéditeur vérifié (variables d'environnement)."""

from __future__ import annotations

import os

import app.core.config  # noqa: F401 — charge `.env`

# Destinataire unique en mode sandbox (BREVO_USE_SIMULATION). Surcharge : BREVO_SANDBOX_RECIPIENT.
_DEFAULT_SANDBOX_RECIPIENT = "skoen7665210@gmail.com"


def brevo_api_key() -> str | None:
    v = os.environ.get("BREVO_API_KEY", "").strip()
    return v or None


def brevo_sender_email() -> str | None:
    v = os.environ.get("BREVO_SENDER_EMAIL", "").strip()
    return v or None


def brevo_sender_name() -> str:
    v = os.environ.get("BREVO_SENDER_NAME", "").strip()
    return v or "Digestic"


def brevo_force_simulation() -> bool:
    """
    Mode test (BREVO_USE_SIMULATION) : aucun e-mail ne doit être remis à un autre destinataire
    que brevo_sandbox_recipient() (API Brevo ou simulation MIME / logs).
    """
    return os.environ.get("BREVO_USE_SIMULATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def brevo_credentials_ok() -> bool:
    """Clé API + expéditeur présents (l’expéditeur doit être validé dans Brevo)."""
    return bool(brevo_api_key() and brevo_sender_email())


def brevo_sandbox_recipient() -> str:
    """Adresse de livraison unique en mode BREVO_USE_SIMULATION."""
    v = os.environ.get("BREVO_SANDBOX_RECIPIENT", "").strip()
    return v if v else _DEFAULT_SANDBOX_RECIPIENT


def brevo_is_configured() -> bool:
    """True si les envois utilisent les vrais destinataires de l’app (hors sandbox)."""
    return brevo_credentials_ok() and not brevo_force_simulation()
