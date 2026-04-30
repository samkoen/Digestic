"""Réduction commerciale appliquée par pharmacie (pourcentage 0–100 sur le montant HT)."""


def normalize_pharmacy_reduction_pct(raw: float | str | None) -> float:
    """Retourne un pourcentage borné entre 0 et 100."""
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        return 0.0
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if v != v:  # NaN
        return 0.0
    return max(0.0, min(100.0, v))


def discounted_line_ht(qty_times_unit_ht_gross: float, reduction_pct: float) -> float:
    """Montant HT ligne après réduction pharmacie (taux exprimé en %)."""
    r = normalize_pharmacy_reduction_pct(reduction_pct)
    return round(float(qty_times_unit_ht_gross) * (1.0 - r / 100.0), 4)


def stacked_line_ht_after_reductions(line_ht_before: float, *reduction_pct_layers: float) -> float:
    """Applique plusieurs réductions % HT successivement (ex. pharmacie puis rapport → BL uniquement).
    Réduction rapport (2ᵉ couche n’atteint pas le BL que via ce calcul sur son dépôt).
    """
    x = float(line_ht_before)
    for p in reduction_pct_layers:
        x = discounted_line_ht(x, p)
    return x


def stacked_equivalent_single_discount_pct(*reduction_pct_layers: float) -> float:
    """Un seul pourcentage d’affichage / API ayant le même effet que la pile HT (pour colonne « Remise »)."""
    layers = tuple(normalize_pharmacy_reduction_pct(p) for p in reduction_pct_layers)
    prod = 1.0
    for r in layers:
        prod *= max(0.0, min(1.0, 1.0 - r / 100.0))
    eq = 100.0 * (1.0 - prod)
    return round(normalize_pharmacy_reduction_pct(eq), 4)
