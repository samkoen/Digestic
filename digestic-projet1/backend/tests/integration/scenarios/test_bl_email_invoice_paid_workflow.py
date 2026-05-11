"""
Scénario : envoi BL par e-mail, facturation, encaissement.

Marqueur : ``integration`` (nécessite ``DATABASE_URL`` / ``.env.test``).

Note produit : la création ``POST .../standalone`` ne envoie pas l’e-mail seule ;
l’envoi transactionnel passe par ``POST .../send-email`` (le service appelle ensuite
``EmailService.send_delivery_note_email`` et marque le bon comme envoyé).
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.services.email_service import EmailService

from tests.support.seed import seed_bl_integration_world

pytestmark = pytest.mark.integration


def _login_admin(client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def test_uc_bl_fac_01_email_bl_invoice_then_mark_paid(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-FAC-01
    Titre:            Envoi BL par e-mail, facturation depuis le BL, encaissement

    Acteur:           administrateur

    Préconditions:
      - pharmacie avec e-mail de notification (seed intégration)
      - stock dépôt suffisant, produit de facturation actif
      - session admin

    Étapes métier:
      1. Créer un BL standalone (statut initial facturable : pending)
      2. Envoyer le BL par e-mail (route transactionnelle ``POST …/send-email``)
      3. Émettre la facture depuis le BL (``POST …/facturer``)
      4. Marquer la facture payée (``POST /api/invoices/{id}/mark-paid``)

    Résultat attendu:
      - Après (2) : ``email_sent`` vrai, statut BL ``sent`` (si pas dépôt-vente)
      - Après (3) : facture en ``pending``, BL ``fully_invoiced`` (facturation totale)
      - Après (4) : facture ``paid``, ``payment_date`` renseignée

    Attendus vérifiés dans le test:
      - Un appel à ``EmailService.send_delivery_note_email`` (preuve envoi BL)
      - Statuts cohérents sur réponses API et GET ressources
    ---------------------------------------------------------------------------
    """

    bl_mail_log: list[dict[str, Any]] = []

    def fake_send_delivery_note_email(
        self,
        to_email: str,
        *,
        pharmacy_name: str,
        bl_number: str | None,
        delivery_date: str | None,
        attachments: Any = None,
    ) -> bool:
        bl_mail_log.append(
            {
                "to_email": to_email,
                "pharmacy_name": pharmacy_name,
                "bl_number": bl_number,
                "delivery_date": delivery_date,
                "has_attachments": bool(attachments),
            }
        )
        return True

    def fake_send_invoice_email(self, *args: Any, **kwargs: Any) -> bool:
        return True

    monkeypatch.setattr(
        EmailService,
        "send_delivery_note_email",
        fake_send_delivery_note_email,
    )
    monkeypatch.setattr(
        EmailService,
        "send_invoice_email",
        fake_send_invoice_email,
    )

    seed = seed_bl_integration_world(db_session)
    db_session.flush()

    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-06-01",
            "bottles_count": 2,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_body = cr.json()
    bl_id = bl_body["id"]
    assert bl_body.get("email_sent") is False
    assert bl_body.get("status") == "pending"

    mail = api_client.post(f"/api/delivery-notes/{bl_id}/send-email", json={})
    assert mail.status_code == 200, mail.text
    mail_payload = mail.json()
    assert mail_payload.get("delivery_note", {}).get("email_sent") is True
    assert mail_payload.get("delivery_note", {}).get("status") == "sent"
    assert len(bl_mail_log) == 1
    assert "@test.digestic.local" in bl_mail_log[0]["to_email"]

    gr = api_client.get(f"/api/delivery-notes/{bl_id}")
    assert gr.status_code == 200
    assert gr.json().get("status") == "sent"
    assert gr.json().get("email_sent") is True

    inv_r = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 2, "amount": 0.0},
    )
    assert inv_r.status_code == 200, inv_r.text
    inv_body = inv_r.json()
    invoice = inv_body["invoice"]
    invoice_id = invoice["id"]
    assert invoice.get("status") == "pending"
    assert inv_body.get("delivery_note", {}).get("status") == "fully_invoiced"

    get_inv = api_client.get(f"/api/invoices/{invoice_id}")
    assert get_inv.status_code == 200
    assert get_inv.json().get("status") == "pending"

    paid_r = api_client.post(
        f"/api/invoices/{invoice_id}/mark-paid",
        json={"local_only": True, "payment_date": "2026-06-15"},
    )
    assert paid_r.status_code == 200, paid_r.text
    assert paid_r.json().get("status") == "paid"
    assert paid_r.json().get("payment_date") is not None

    get_inv2 = api_client.get(f"/api/invoices/{invoice_id}")
    assert get_inv2.status_code == 200
    assert get_inv2.json().get("status") == "paid"
