"""Scénario : note terrain v1 via GET /api/planning/evaluation."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from tests.support.evaluation_seed import insert_visit_reports_for_evaluation_v1
from tests.support.seed import seed_bl_integration_world

pytestmark = pytest.mark.integration


def _login_admin(client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text


def test_planning_evaluation_v1_api_expected_composite(
    api_client,
    db_session: Session,
):
    seed = seed_bl_integration_world(db_session)
    anchor = date(2026, 6, 15)
    insert_visit_reports_for_evaluation_v1(
        db_session,
        pharmacy_id=seed.pharmacy_id,
        commercial_id=seed.commercial_id,
        anchor_day=anchor,
    )
    db_session.flush()

    _login_admin(api_client, seed.admin_email, seed.admin_password)

    r = api_client.get(
        "/api/planning/evaluation",
        params={
            "start_date": anchor.isoformat(),
            "end_date": anchor.isoformat(),
            "commercial_id": str(seed.commercial_id),
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report_count"] == 4
    assert body["composite_0_100"] == pytest.approx(78.9, rel=1e-2)
    assert body["subscores"]["completion"]["value_0_100"] == 75.0
