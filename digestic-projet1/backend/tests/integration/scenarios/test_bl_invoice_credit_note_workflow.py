"""
Scénario : BL, facturation, puis annulation par avoir total.

Marqueur : ``integration`` (``DATABASE_URL`` / ``.env.test``).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.services.email_service import EmailService

from tests.support.seed import seed_bl_integration_world

pytestmark = pytest.mark.integration


def _login_admin(client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def test_uc_bl_fac_avoir_01_invoice_total_credit_note_statuses(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-FAC-AVOIR-01
    Titre:            Facture depuis BL puis annulation par avoir (total)

    Acteur:           administrateur

    Préconditions:
      - jeu seed intégration (pharmacie, stock, produit facturation, admin)
      - facture émise via VosFactures mock (``vosfactures_mock``) pour permettre l’avoir

    Étapes métier:
      1. Créer un BL standalone facturable (``pending``)
      2. Émettre la facture pour la totalité du BL (``POST …/facturer``)
      3. Émettre un avoir total sur la facture (``POST /api/invoices/{id}/credit-notes``)

    Résultat attendu (comportement actuel Digestic):
      - Après (2) : BL ``fully_invoiced``, facture ``pending``, ``external_provider`` mock
      - Après (3) : facture ``credited`` ; document d’avoir en statut ``issued`` (scope ``full``)
      - Le BL reste ``fully_invoiced`` (l’avoir ne rouvre pas le bon pour refacturation)

    Vérifications test:
      - GET BL, GET facture, POST credit-notes, GET liste avoirs pour la facture
    ---------------------------------------------------------------------------
    """

    monkeypatch.setattr(
        EmailService,
        "send_invoice_email",
        lambda *args, **kwargs: True,
    )

    seed = seed_bl_integration_world(db_session)
    db_session.flush()

    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-07-01",
            "bottles_count": 3,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_id = cr.json()["id"]

    inv_r = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 3, "amount": 0.0},
    )
    assert inv_r.status_code == 200, inv_r.text
    body = inv_r.json()
    invoice = body["invoice"]
    invoice_id = invoice["id"]
    dn_after = body.get("delivery_note") or {}

    assert dn_after.get("status") == "fully_invoiced"
    assert invoice.get("status") == "pending"
    assert (invoice.get("external_provider") or "").strip().lower() in (
        "vosfactures",
        "vosfactures_mock",
    )
    assert (invoice.get("external_invoice_id") or "").strip()

    get_bl = api_client.get(f"/api/delivery-notes/{bl_id}")
    assert get_bl.status_code == 200
    assert get_bl.json().get("status") == "fully_invoiced"

    cn_r = api_client.post(
        f"/api/invoices/{invoice_id}/credit-notes",
        json={"correction_reason": "Test intégration — annulation facture (avoir total)."},
    )
    assert cn_r.status_code == 201, cn_r.text
    credit_note = cn_r.json()
    cn_id = credit_note["id"]
    assert credit_note.get("status") == "issued"
    assert credit_note.get("credit_scope") == "full"
    assert (credit_note.get("external_provider") or "").strip().lower() in (
        "vosfactures",
        "vosfactures_mock",
    )

    get_inv = api_client.get(f"/api/invoices/{invoice_id}")
    assert get_inv.status_code == 200
    inv_final = get_inv.json()
    assert inv_final.get("status") == "credited"

    list_cn = api_client.get(f"/api/invoices/{invoice_id}/credit-notes")
    assert list_cn.status_code == 200
    items = list_cn.json()
    assert isinstance(items, list) and len(items) >= 1
    match = next((x for x in items if x.get("id") == cn_id), items[0])
    assert match.get("status") == "issued"
    assert match.get("source_invoice_id") == invoice_id

    get_bl_end = api_client.get(f"/api/delivery-notes/{bl_id}")
    assert get_bl_end.status_code == 200
    assert get_bl_end.json().get("status") == "fully_invoiced"
