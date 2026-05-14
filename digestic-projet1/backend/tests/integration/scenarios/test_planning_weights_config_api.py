"""API : révisions des poids planning (distinct note terrain v1)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from tests.support.seed import seed_bl_integration_world

pytestmark = pytest.mark.integration


def _login_admin(client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def test_planning_weights_config_active_returns_snapshot(api_client, db_session: Session):
    seed = seed_bl_integration_world(db_session)
    db_session.commit()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    r = api_client.get("/api/planning/weights-config/active")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "effective_weights" in body
    assert body["effective_weights"]["visits_max_per_day"] == 14


def test_planning_weights_revision_crud_admin(api_client, db_session: Session):
    seed = seed_bl_integration_world(db_session)
    db_session.commit()
    _login_admin(api_client, seed.admin_email, seed.admin_password)

    base = api_client.get("/api/planning/weights-config/active").json()
    w = dict(base["effective_weights"])
    w["geo_weight"] = 9.5

    cr = api_client.post(
        "/api/planning/weights-revisions",
        json={"weights": w, "label": "test-unit", "set_active": True},
    )
    assert cr.status_code == 200, cr.text
    rev_id = cr.json()["revision"]["id"]

    chk = api_client.get("/api/planning/weights-config/active").json()
    assert chk["effective_weights"]["geo_weight"] == pytest.approx(9.5)

    lst = api_client.get("/api/planning/weights-revisions", params={"limit": 5})
    assert lst.status_code == 200
    ids = [x["id"] for x in lst.json().get("revisions", [])]
    assert rev_id in ids

    runs = api_client.get("/api/planning/runs", params={"limit": 5})
    assert runs.status_code == 200
