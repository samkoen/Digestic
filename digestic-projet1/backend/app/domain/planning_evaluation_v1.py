"""
Évaluation qualitative du terrain — **formule figée version v1**.

Objectif : produire une note agrégée **0–100** à partir des **rapports de visite**
réels (`visit_reports`), incluant le **ressenti** (`feeling_rating`) lorsqu’il est renseigné.

La somme des pondérations **COMPLETION_WEIGHT + STOCK_WEIGHT + FEELING_WEIGHT** vaut **1**.
Toute évolution métier doit porter un nouveau **VERSION** et document explicite des changements.
"""
from __future__ import annotations

from typing import Any

VERSION = "v1"

COMPLETION_WEIGHT = 0.35
STOCK_WEIGHT = 0.35
FEELING_WEIGHT = 0.30

# Hypothèse neutre pour le bloc « ressenti » lorsqu’aucune note na’a été laissée sur la période.
FEELING_NEUTRAL_WHEN_MISSING = 70.0

# Points 0–100 par statut stock déclaré au rapport (hors « completed », le statut stock reste lu tel quel).
_STOCK_POINTS: dict[str, float] = {
    "good": 100.0,
    "unknown": 72.0,
    "low": 45.0,
    "out_of_stock": 15.0,
}

FORMULA_DOCUMENTATION_FR = """
## Note agrégée terrain — version v1

**Période** : filtres sur la date civile du champ `visit_reports.visit_date` (bornes inclusives).

### Sous-score « réalisation » (0–100), pondération {:.0%}
Parmi tous les rapports de la période : proportion de rapports avec `visit_status == completed`,
multipliée par 100.

### Sous-score « stock déclaré » (0–100), pondération {:.0%}
Moyenne des scores suivants pour **chaque** rapport (statut `stock_status`) :
- `good` → 100
- `unknown` → 72
- `low` → 45
- `out_of_stock` → 15  
(autres valeurs → traitées comme `unknown`)

### Sous-score « ressenti » (0–100), pondération {:.0%}
Si au moins un rapport possède `feeling_rating` entre 1 et 5 : moyenne des valeurs
`(rating - 1) / 4 × 100` (donc 1 → 0, 5 → 100).

Si **aucun** ressenti n’est renseigné sur la période : on applique la constante neutre **{} / 100**
documentée comme hypothèse (pour ne pas faire peser à tort les deux autres axes).

### Composite
`note = {:.0%} × réalisation + {:.0%} × stock + {:.0%} × ressenti`  
(arrondi à une décimale côté API).

---
*Cette définition est normative pour VERSION={}. Toute modification implique VERSION+1.*
""".strip().format(
    COMPLETION_WEIGHT,
    STOCK_WEIGHT,
    FEELING_WEIGHT,
    int(FEELING_NEUTRAL_WHEN_MISSING),
    COMPLETION_WEIGHT,
    STOCK_WEIGHT,
    FEELING_WEIGHT,
    VERSION,
)


def _norm_stock_key(raw: str | None) -> str:
    s = (raw or "").strip().lower().replace("-", "_")
    return s if s else "unknown"


def completion_subscore(completed_count: int, total_reports: int) -> float | None:
    if total_reports <= 0:
        return None
    return round(100.0 * completed_count / total_reports, 2)


def stock_subscore_from_statuses(statuses: list[str]) -> float | None:
    if not statuses:
        return None
    total = 0.0
    for st in statuses:
        key = _norm_stock_key(st)
        total += float(_STOCK_POINTS.get(key, _STOCK_POINTS["unknown"]))
    return round(total / len(statuses), 2)


def feeling_subscore_from_ratings(ratings: list[int]) -> tuple[float | None, bool]:
    """
    Retourne (score 0–100 ou None si aucune donnée exploitable, neutral_assumption_used).
    """
    clean = [int(r) for r in ratings if r is not None and 1 <= int(r) <= 5]
    if not clean:
        return None, True
    pts = [(r - 1) / 4.0 * 100.0 for r in clean]
    return round(sum(pts) / len(pts), 2), False


def composite_note(
    completion: float | None,
    stock: float | None,
    feeling: float | None,
    *,
    neutral_feeling: float = FEELING_NEUTRAL_WHEN_MISSING,
) -> float | None:
    """Combine les trois sous-scores ; `feeling` None déclenche la valeur neutre."""
    if completion is None or stock is None:
        return None
    feel = feeling if feeling is not None else neutral_feeling
    raw = (
        COMPLETION_WEIGHT * completion
        + STOCK_WEIGHT * stock
        + FEELING_WEIGHT * feel
    )
    return round(min(100.0, max(0.0, raw)), 1)


def build_breakdown(
    *,
    completed_count: int,
    total_reports: int,
    stock_statuses: list[str],
    feeling_ratings: list[int],
) -> dict[str, Any]:
    """Construit le détail exposé par l’API (champs sérialisables)."""
    comp = completion_subscore(completed_count, total_reports)
    stk = stock_subscore_from_statuses(stock_statuses)
    feel_raw, neutral_used = feeling_subscore_from_ratings(feeling_ratings)
    feel_display = feel_raw if feel_raw is not None else FEELING_NEUTRAL_WHEN_MISSING
    composite = composite_note(comp, stk, feel_raw)

    return {
        "version": VERSION,
        "report_count": total_reports,
        "counts": {
            "completed_visits": completed_count,
            "not_completed_visits": max(0, total_reports - completed_count),
        },
        "subscores": {
            "completion": {
                "value_0_100": comp,
                "weight": COMPLETION_WEIGHT,
                "description_fr": "Part des rapports « visite effectuée ».",
            },
            "stock_declared": {
                "value_0_100": stk,
                "weight": STOCK_WEIGHT,
                "description_fr": "Moyenne des scores attribués au stock déclaré sur chaque rapport.",
            },
            "feeling": {
                "value_0_100": round(feel_display, 2),
                "weight": FEELING_WEIGHT,
                "ratings_used_count": len(
                    [r for r in feeling_ratings if r is not None and 1 <= int(r) <= 5]
                ),
                "neutral_assumption_used": neutral_used,
                "description_fr": (
                    "Moyenne du ressenti (1–→100), ou valeur neutre si aucune note."
                ),
            },
        },
        "composite_0_100": composite,
        "formula_documentation_fr": FORMULA_DOCUMENTATION_FR,
    }
