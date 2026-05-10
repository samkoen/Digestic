"""Envoi d'e-mails transactionnels via l'API Brevo (POST /v3/smtp/email)."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.integrations.brevo.config import (
    brevo_api_key,
    brevo_sender_email,
    brevo_sender_name,
)

logger = logging.getLogger(__name__)

BREVO_SMTP_API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoApiError(Exception):
    """Erreur HTTP ou réponse inattendue de l'API Brevo."""


def _sanitize_attachment_name(name: str, fallback: str = "piece-jointe.pdf") -> str:
    s = (name or "").strip() or fallback
    safe = "".join(c if c.isalnum() or c in " ._-()" else "_" for c in s)
    out = safe[:120] if safe else fallback
    if not out.lower().endswith(".pdf"):
        out = f"{out}.pdf"
    return out


def send_transactional_html_email(
    *,
    to_email: str,
    subject: str,
    html_content: str,
    attachments: list[tuple[bytes, str]] | None = None,
) -> dict[str, Any]:
    """
    Envoie un e-mail HTML avec pièces jointes optionnelles (PDF en base64).
    Nécessite BREVO_API_KEY et BREVO_SENDER_EMAIL (expéditeur vérifié dans l'espace Brevo).
    """
    key = brevo_api_key()
    sender = brevo_sender_email()
    if not key or not sender:
        raise BrevoApiError("Brevo : BREVO_API_KEY et BREVO_SENDER_EMAIL requis")

    to_addr = (to_email or "").strip()
    if not to_addr:
        raise BrevoApiError("Destinataire vide")

    payload: dict[str, Any] = {
        "sender": {"name": brevo_sender_name(), "email": sender},
        "to": [{"email": to_addr}],
        "subject": (subject or "").strip() or "(sans objet)",
        "htmlContent": html_content or "<p></p>",
    }
    if attachments:
        payload["attachment"] = [
            {
                "content": base64.standard_b64encode(data).decode("ascii"),
                "name": _sanitize_attachment_name(fname),
            }
            for data, fname in attachments
            if data
        ]

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(BREVO_SMTP_API_URL, data=body, method="POST")
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("api-key", key)

    try:
        with urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status not in (200, 201, 202):
                raise BrevoApiError(f"Brevo HTTP {resp.status}: {raw[:500]}")
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        msg = err_body[:800]
        try:
            parsed = json.loads(err_body) if err_body else {}
            if isinstance(parsed, dict) and parsed.get("message"):
                msg = str(parsed.get("message"))
        except json.JSONDecodeError:
            pass
        logger.warning("Brevo HTTP %s: %s", e.code, msg)
        raise BrevoApiError(f"Brevo HTTP {e.code}: {msg}") from e

    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {"raw": raw}
