"""Codes d’alerte du moteur de planning et libellés destinés aux humains / e-mails."""

from __future__ import annotations

from typing import Final

# Alerte : RDV « dur » un jour où visits_max_per_day est déjà atteint → date gardée quand même.
PLANNING_RDV_HARD_EMAIL_ALERT_CODES: Final[frozenset[str]] = frozenset(
    {
        "rdv_dur_capacity_depassee_assigne_quand_meme",
        "rdv_dur_sur_jour_non_travaille",
    }
)


def humanize_planning_alert_code(code: str) -> str:
    if code == "rdv_dur_capacity_depassee_assigne_quand_meme":
        return (
            "Jour du RDV fixe déjà à la charge maximale : la date du RDV est conservée malgré tout."
        )
    if code == "rdv_dur_sur_jour_non_travaille":
        return (
            "RDV fixe un jour fermé dans votre calendrier (weekend, congé ou date bloquée) : "
            "la date du RDV est conservée avec alerte."
        )
    if code == "charge_max_journaliere_glouton_fallback":
        return "Capacité journalière max atteinte ; affectation de repli."
    if code == "planning_cap_horizon_saturation_skip":
        return (
            "Plus de créneaux disponibles sous le plafond journalier sur vos jours ouvrés dans cet horizon "
            "(calendrier planning inclus) : cette pharmacie n’a pas été réassignée automatiquement "
            "(date de passage inchangée en base)."
        )
    if code == "planning_calendrier_sature_etale_hors_preferences":
        return (
            "Jours préférés (calendrier) déjà saturés pour ce commercial : étalement du passage sur une autre journée "
            "de l’horizon hors préférence, pour respecter le plafond journalier."
        )
    return code


def split_planning_alert_tokens(raw: str | None) -> list[str]:
    return [x.strip() for x in (raw or "").split(";") if x.strip()]


def humanize_planning_alert_for_email(raw: str | None) -> str:
    """Libellés concaténés pour les codes pertinentes notifications e-mail RDV."""
    tokens = split_planning_alert_tokens(raw)
    relevant = [t for t in tokens if t in PLANNING_RDV_HARD_EMAIL_ALERT_CODES]
    if relevant:
        return " ; ".join(humanize_planning_alert_code(t) for t in relevant)
    if tokens:
        return " ; ".join(humanize_planning_alert_code(t) for t in tokens)
    return raw or ""
