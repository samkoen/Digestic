"""Semaine de retour prévue : (année ISO, numéro de semaine ISO) après N semaines."""
from __future__ import annotations

from datetime import date, timedelta


def iso_week_and_year_after_n_weeks(weeks_ahead: int) -> tuple[int, int]:
    """
    Retourne (année_ISO, numéro_de_semaine_ISO) de la date « aujourd’hui + N semaines ».
    Ex. : semaine 4 + 2 semaines → (Y, 6) si on tombe en semaine 6 la même année.
    """
    n = int(weeks_ahead)
    if n < 1 or n > 10:
        raise ValueError("weeks_ahead doit être entre 1 et 10")
    d = date.today() + timedelta(weeks=n)
    y, w, _ = d.isocalendar()
    return (int(y), int(w))
