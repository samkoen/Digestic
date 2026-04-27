"""Configuration VosFactures via variables d'environnement (aucun secret dans le code)."""

from __future__ import annotations

import os

import app.core.config  # noqa: F401 — charge `.env`


def vosfactures_api_token() -> str | None:
    v = os.environ.get("VOSFACTURES_API_TOKEN", "").strip()
    return v or None


def vosfactures_subdomain() -> str | None:
    """Sous-domaine seul : pour https://moncompte.vosfactures.fr → « moncompte »."""
    v = os.environ.get("VOSFACTURES_SUBDOMAIN", "").strip().lower()
    if not v:
        return None
    v = v.removeprefix("https://").removeprefix("http://")
    if "/" in v:
        v = v.split("/")[0]
    for suffix in (".vosfactures.fr", ".vosfactures"):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
    return v or None


def vosfactures_department_id() -> int | None:
    raw = os.environ.get("VOSFACTURES_DEPARTMENT_ID", "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def vosfactures_seller_name() -> str:
    """Raison sociale émetteur affichée sur la facture (obligatoire côté API invoices.json)."""
    v = os.environ.get("VOSFACTURES_SELLER_NAME", "").strip()
    if v:
        return v
    # Valeur par défaut pour ne pas bloquer si non renseigné ; à surcharger par .env en production.
    return "Digestic"


def vosfactures_test_documents() -> bool:
    return os.environ.get("VOSFACTURES_TEST", "").lower() in ("1", "true", "yes", "on")


def vosfactures_force_mock() -> bool:
    """Forcer le client mock (ex. CI sans réseau)."""
    return os.environ.get("VOSFACTURES_USE_MOCK", "").lower() in ("1", "true", "yes", "on")


def vosfactures_is_configured() -> bool:
    return bool(vosfactures_api_token() and vosfactures_subdomain() and not vosfactures_force_mock())
