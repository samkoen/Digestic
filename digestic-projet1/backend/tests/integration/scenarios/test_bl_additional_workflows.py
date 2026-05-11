"""
Scénarios d'intégration supplémentaires (BL, factures, avoirs, rectificatif).

Marqueur : ``integration``.
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


def _patch_invoice_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        EmailService,
        "send_invoice_email",
        lambda *a, **k: True,
    )


def test_uc_bl_fac_02_partial_invoice_then_remainder_fully_invoiced(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-FAC-02
    Titre:            Facturation partielle puis solde sur le même BL

    Acteur:           administrateur

    Préconditions:    seed intégration, BL ``pending`` avec plusieurs bouteilles

    Étapes:
      1. Créer un BL de 5 bouteilles
      2. Facturer 2 bouteilles (partiel)
      3. Vérifier reste 3 bouteilles, BL non ``fully_invoiced``
      4. Facturer les 3 restantes

    Résultat attendu:
      - Après (2) : ``bottles_count`` = 3, statut inchangé (facturable)
      - Après (4) : BL ``fully_invoiced``, ``bottles_count`` = 0
    ---------------------------------------------------------------------------
    """
    _patch_invoice_email(monkeypatch)

    seed = seed_bl_integration_world(db_session)
    db_session.flush()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-08-01",
            "bottles_count": 5,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_id = cr.json()["id"]

    inv1 = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 2, "amount": 0.0},
    )
    assert inv1.status_code == 200, inv1.text
    dn1 = inv1.json().get("delivery_note") or {}
    assert dn1.get("bottles_count") == 3
    assert dn1.get("status") != "fully_invoiced"

    get_bl = api_client.get(f"/api/delivery-notes/{bl_id}")
    assert get_bl.json().get("bottles_count") == 3

    inv2 = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 3, "amount": 0.0},
    )
    assert inv2.status_code == 200, inv2.text
    dn2 = inv2.json().get("delivery_note") or {}
    assert dn2.get("status") == "fully_invoiced"
    assert dn2.get("bottles_count") == 0


def test_uc_bl_fac_avoir_02_second_total_credit_rejected(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-FAC-AVOIR-02
    Titre:            Refus d'un second avoir total sur une facture déjà créditée

    Acteur:           administrateur (API)

    Étapes:
      1. BL + facturation totale
      2. Avoir total (facture ``credited``)
      3. Nouvelle tentative d'avoir total sur la même facture

    Résultat attendu:
      - Étape 3 : erreur 400, message sur statut définitif / créditée
    ---------------------------------------------------------------------------
    """
    _patch_invoice_email(monkeypatch)

    seed = seed_bl_integration_world(db_session)
    db_session.flush()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-08-02",
            "bottles_count": 2,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_id = cr.json()["id"]

    inv_r = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 2, "amount": 0.0},
    )
    assert inv_r.status_code == 200, inv_r.text
    invoice_id = inv_r.json()["invoice"]["id"]

    cn1 = api_client.post(
        f"/api/invoices/{invoice_id}/credit-notes",
        json={"correction_reason": "Premier avoir test intégration."},
    )
    assert cn1.status_code == 201, cn1.text

    cn2 = api_client.post(
        f"/api/invoices/{invoice_id}/credit-notes",
        json={"correction_reason": "Second avoir doit échouer."},
    )
    assert cn2.status_code == 400
    err = (cn2.json().get("error") or "").lower()
    assert "définitif" in err or "credited" in err


def test_uc_bl_adm_01_rectifier_cancels_source_and_creates_new_bl(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-ADM-01
    Titre:            Bon rectificatif (annulation source + nouveau BL)

    Acteur:           administrateur

    Étapes:
      1. Créer un BL standalone (ex. 4 bouteilles)
      2. Appeler ``POST …/rectifier`` avec nouvelles quantités et date

    Résultat attendu:
      - Bon source ``cancelled``
      - Nouveau bon distinct, quantités conformes au payload
      - Réponse inclut ``replaced_deposit_id`` (lien vers l'ancien id)
    ---------------------------------------------------------------------------
    """
    _patch_invoice_email(monkeypatch)

    seed = seed_bl_integration_world(db_session)
    db_session.flush()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-08-03",
            "bottles_count": 4,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    old_id = cr.json()["id"]

    rect = api_client.post(
        f"/api/delivery-notes/{old_id}/rectifier",
        json={
            "delivery_date": "2026-08-04",
            "bottles_count": 2,
            "free_units_quantity": 1,
            "bl_billing_mode": "pending",
        },
    )
    assert rect.status_code == 201, rect.text
    payload = rect.json()
    assert payload.get("replaced_deposit_id") == old_id
    new_id = payload.get("id")
    assert new_id and new_id != old_id
    assert payload.get("bottles_count") == 2
    assert payload.get("free_units_quantity") == 1
    assert payload.get("status") == "pending"

    old = api_client.get(f"/api/delivery-notes/{old_id}")
    assert old.status_code == 200
    assert old.json().get("status") == "cancelled"


def test_uc_fac_02_paid_invoice_then_total_credit_note(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-FAC-02
    Titre:            Facture encaissée puis annulation par avoir total

    Acteur:           administrateur

    Étapes:
      1. BL + facturation totale
      2. Marquer la facture payée (``mark-paid``, ``local_only``)
      3. Émettre un avoir total

    Résultat attendu:
      - Après (2) : statut ``paid``
      - Après (3) : facture ``credited`` ; avoir ``issued``
    ---------------------------------------------------------------------------
    """
    _patch_invoice_email(monkeypatch)

    seed = seed_bl_integration_world(db_session)
    db_session.flush()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-08-05",
            "bottles_count": 2,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_id = cr.json()["id"]

    inv_r = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 2, "amount": 0.0},
    )
    assert inv_r.status_code == 200, inv_r.text
    invoice_id = inv_r.json()["invoice"]["id"]

    paid = api_client.post(
        f"/api/invoices/{invoice_id}/mark-paid",
        json={"local_only": True, "payment_date": "2026-08-10"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json().get("status") == "paid"

    cn = api_client.post(
        f"/api/invoices/{invoice_id}/credit-notes",
        json={"correction_reason": "Avoir après encaissement — test intégration."},
    )
    assert cn.status_code == 201, cn.text
    assert cn.json().get("status") == "issued"

    final = api_client.get(f"/api/invoices/{invoice_id}")
    assert final.json().get("status") == "credited"


def test_uc_bl_fac_03_cannot_reinvoice_after_fully_invoiced(
    api_client,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    ---------------------------------------------------------------------------
    Fiche UC
    ---------------------------------------------------------------------------
    UC_ID:            UC-BL-FAC-03
    Titre:            Impossible de facturer à nouveau un BL déjà entièrement facturé

    Acteur:           API

    Étapes:
      1. BL + facturation totale (``fully_invoiced``, 0 bouteille)
      2. Nouvelle tentative ``POST …/facturer``

    Résultat attendu:
      - Étape 2 : 400, message sur quantité invalide
    ---------------------------------------------------------------------------
    """
    _patch_invoice_email(monkeypatch)

    seed = seed_bl_integration_world(db_session)
    db_session.flush()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    cr = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-08-06",
            "bottles_count": 1,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert cr.status_code == 201, cr.text
    bl_id = cr.json()["id"]

    inv1 = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 1, "amount": 0.0},
    )
    assert inv1.status_code == 200, inv1.text
    assert inv1.json()["delivery_note"].get("status") == "fully_invoiced"

    inv2 = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 1, "amount": 0.0},
    )
    assert inv2.status_code == 400
    err = (inv2.json().get("error") or "").lower()
    assert "invalide" in err or "0" in err
