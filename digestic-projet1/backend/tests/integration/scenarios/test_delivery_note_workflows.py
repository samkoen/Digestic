"""
Scénarios : création BL, annulation, facturation ; dépôt-vente puis facturation.

Marqueur : ``integration`` (nécessite ``DATABASE_URL``).
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.support.seed import seed_bl_integration_world

pytestmark = pytest.mark.integration


def _login_admin(client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


@pytest.mark.usefixtures("no_transactional_email")
def test_create_bl_cancel_then_invoice_rejected(
    api_client,
    db_session: Session,
):
    """
    UC : BL en pending → annulation admin → tentative de facturation refusée.
    """
    seed = seed_bl_integration_world(db_session)
    db_session.flush()

    _login_admin(api_client, seed.admin_email, seed.admin_password)

    create = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-05-10",
            "bottles_count": 4,
            "free_units_quantity": 0,
            "bl_billing_mode": "pending",
        },
    )
    assert create.status_code == 201, create.text
    bl_id = create.json()["id"]

    cancel = api_client.post(f"/api/delivery-notes/{bl_id}/annuler")
    assert cancel.status_code == 200, cancel.text
    assert cancel.json().get("status") == "cancelled"

    invoice_try = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 4, "amount": 0},
    )
    assert invoice_try.status_code == 400
    assert "annulé" in (invoice_try.json().get("error") or "").lower()


@pytest.mark.usefixtures("no_transactional_email")
def test_depot_vente_validate_then_invoice_ok(
    api_client,
    db_session: Session,
):
    """
    UC : BL dépôt-vente → facturation refusée → validation → facturation OK.
    """
    seed = seed_bl_integration_world(db_session)
    db_session.flush()

    _login_admin(api_client, seed.admin_email, seed.admin_password)

    create = api_client.post(
        "/api/delivery-notes/standalone",
        json={
            "pharmacy_id": str(seed.pharmacy_id),
            "delivery_date": "2026-05-11",
            "bottles_count": 3,
            "free_units_quantity": 0,
            "bl_billing_mode": "depot_vente",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    bl_id = body["id"]
    assert body.get("status") == "depot-vente"

    blocked = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 3, "amount": 0},
    )
    assert blocked.status_code == 400
    assert "dépôt-vente" in (blocked.json().get("error") or "").lower()

    ok_pending = api_client.post(f"/api/delivery-notes/{bl_id}/valider-depot-vente")
    assert ok_pending.status_code == 200, ok_pending.text
    assert ok_pending.json().get("status") == "pending"

    inv = api_client.post(
        f"/api/delivery-notes/{bl_id}/facturer",
        json={"bottles_to_invoice": 3, "amount": 0},
    )
    assert inv.status_code == 200, inv.text
    payload = inv.json()
    assert payload.get("invoice")
    assert payload["invoice"].get("invoice_number")
    assert payload.get("delivery_note", {}).get("status") == "fully_invoiced"
