"""Intégration Brevo (e-mails transactionnels)."""

from app.integrations.brevo.client import BrevoApiError, send_transactional_html_email
from app.integrations.brevo.config import brevo_credentials_ok, brevo_is_configured

__all__ = [
    "BrevoApiError",
    "brevo_credentials_ok",
    "brevo_is_configured",
    "send_transactional_html_email",
]
