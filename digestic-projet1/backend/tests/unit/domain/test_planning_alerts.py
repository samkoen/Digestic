"""Tests unitaires — codes d’alerte planning agrégées."""

from __future__ import annotations

from app.domain.planning_alerts import (
    PLANNING_RDV_HARD_EMAIL_ALERT_CODES,
    humanize_planning_alert_for_email,
    split_planning_alert_tokens,
)


def test_split_compound_codes():
    assert split_planning_alert_tokens(
        "rdv_dur_capacity_depassee_assigne_quand_meme;rdv_dur_sur_jour_non_travaille"
    ) == [
        "rdv_dur_capacity_depassee_assigne_quand_meme",
        "rdv_dur_sur_jour_non_travaille",
    ]


def test_humanize_two_email_codes():
    s = humanize_planning_alert_for_email(
        "rdv_dur_capacity_depassee_assigne_quand_meme;rdv_dur_sur_jour_non_travaille"
    )
    assert "charge maximale" in s.lower()
    assert "jour fermé" in s.lower()


def test_email_constants_cover_rdv_calendar():
    assert "rdv_dur_sur_jour_non_travaille" in PLANNING_RDV_HARD_EMAIL_ALERT_CODES
