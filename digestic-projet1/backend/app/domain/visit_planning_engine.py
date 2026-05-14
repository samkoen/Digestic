"""
Algorithme de planning automatique (hybride : besoins / semaine ISO / quartier léger / géo faible).

La géographie ne peut pas contrebalancer un fort écart de besoin : elle intervient via un coefficient
`geo_weight` typiquement bas par rapport aux scores stock / retard / fenêtre semaine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Any


def _parse_date_maybe(v: str | date | datetime | None) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return date.fromisoformat(s[:10])
    return None


def _iso_week_key(d: date) -> tuple[int, int]:
    w = d.isocalendar()
    return (int(w[0]), int(w[1]))


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(p1) * cos(p2) * sin(d_lambda / 2) ** 2
    return 2 * r * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))


def district_key(postal_code: str | None, city: str | None) -> str:
    pc = (postal_code or "").strip()[:4]
    c = (city or "").strip().upper()[:32]
    return f"{pc}|{c}"


@dataclass
class PlanningWeights:
    stock_out: float = 120.0
    stock_low: float = 55.0
    failed_closed: float = 48.0
    failed_other: float = 22.0
    """Malus géographique (km) ramené au même ordre que les besoins mais avec un poids faible."""
    per_day_overdue: float = 10.0
    max_overdue_bonus: float = 90.0
    in_target_week: float = 72.0
    geo_weight: float = 8.0
    fill_radius_km: float = 14.0
    district_density: float = 6.0
    visits_max_per_day: int = 14
    default_cycle_days: int = 28
    orphan_horizon_bonus_days: int = 10

    @classmethod
    def merge(cls, overrides: dict[str, Any] | None) -> PlanningWeights:
        if not overrides:
            return cls()
        base = cls()
        kw: dict[str, Any] = {}
        for k, v in overrides.items():
            if hasattr(base, k) and v is not None:
                t = type(getattr(base, k))
                if t is bool:
                    kw[k] = bool(v)
                elif t is int:
                    kw[k] = int(v)
                else:
                    kw[k] = float(v)
        return cls(**{**base.__dict__, **kw})


@dataclass
class PharmacyPlanningInputs:
    id: str
    commercial_id: str
    district: str
    latitude: float | None
    longitude: float | None
    next_visit_date: date | None
    planning_hard_rdv_date: date | None
    last_visit_date: date | None
    stock_status: str
    visit_failed_reason: str | None


@dataclass
class PlanningResult:
    assignments: dict[str, date]
    alerts: dict[str, str]
    diagnostics: dict[str, Any] = field(default_factory=dict)


def _soft_anchor(p: PharmacyPlanningInputs, ref: date, w: PlanningWeights) -> date:
    if p.next_visit_date:
        return p.next_visit_date
    if p.last_visit_date:
        return p.last_visit_date + timedelta(days=w.default_cycle_days)
    return ref + timedelta(days=min(w.orphan_horizon_bonus_days, 7))


def _base_need_for_day(p: PharmacyPlanningInputs, day: date, ref: date, w: PlanningWeights) -> float:
    score = 0.0
    st = (p.stock_status or "unknown").lower()
    if st == "out_of_stock":
        score += w.stock_out
    elif st == "low":
        score += w.stock_low

    rsn = (p.visit_failed_reason or "").strip().lower()
    if rsn == "pharmacy_closed":
        score += w.failed_closed
    elif rsn:
        score += w.failed_other

    anchor = _soft_anchor(p, ref, w)
    overdue = max(0, (ref - anchor).days)
    score += min(w.max_overdue_bonus, overdue * w.per_day_overdue)

    if _iso_week_key(anchor) == _iso_week_key(day):
        score += w.in_target_week
    return score


def _centroid(day_centroids: dict[date, tuple[float, float, int]], d: date) -> tuple[float, float] | None:
    t = day_centroids.get(d)
    if not t:
        return None
    lat_s, lon_s, n = t
    if n <= 0:
        return None
    return (lat_s / n, lon_s / n)


def _geo_term(
    p: PharmacyPlanningInputs,
    day: date,
    day_centroids: dict[date, tuple[float, float, int]],
    w: PlanningWeights,
) -> float:
    if p.latitude is None or p.longitude is None:
        return w.geo_weight * 0.35
    c = _centroid(day_centroids, day)
    if c is None:
        return w.geo_weight * 0.45
    dist = haversine_km(p.latitude, p.longitude, c[0], c[1])
    prox = max(0.0, 1.0 - min(1.0, dist / max(1.0, w.fill_radius_km)))
    return w.geo_weight * prox


def _density_bonus(
    p: PharmacyPlanningInputs,
    day: date,
    district_count: dict[tuple[date, str], int],
    w: PlanningWeights,
) -> float:
    k = (day, p.district)
    others = max(0, district_count.get(k, 0))
    return w.district_density * others


def _register_day_visit(
    p: PharmacyPlanningInputs,
    day: date,
    day_load: dict[date, int],
    district_count: dict[tuple[date, str], int],
    day_centroids: dict[date, tuple[float, float, int]],
) -> None:
    day_load[day] = day_load.get(day, 0) + 1
    district_count[(day, p.district)] = district_count.get((day, p.district), 0) + 1
    if p.latitude is not None and p.longitude is not None:
        cur = day_centroids.get(day)
        if cur is None:
            day_centroids[day] = (p.latitude, p.longitude, 1)
        else:
            la, lo, n = cur
            day_centroids[day] = (la + p.latitude, lo + p.longitude, n + 1)


def _clamp(day: date, start: date, end: date) -> date:
    if day < start:
        return start
    if day > end:
        return end
    return day


def run_planning_assignment(
    rows: list[PharmacyPlanningInputs],
    reference_date: date,
    horizon_days: int,
    weights: PlanningWeights,
) -> PlanningResult:
    if horizon_days < 1:
        horizon_days = 1
    horizon = [reference_date + timedelta(days=i) for i in range(horizon_days)]
    start_d, end_d = horizon[0], horizon[-1]

    alerts: dict[str, str] = {}
    assignments: dict[str, date] = {}
    day_load: dict[date, int] = {d: 0 for d in horizon}
    district_count: dict[tuple[date, str], int] = {}
    day_centroids: dict[date, tuple[float, float, int]] = {}

    hard_group: list[PharmacyPlanningInputs] = []
    flex_group: list[PharmacyPlanningInputs] = []
    seen: set[str] = set()

    for p in rows:
        if not p.id or p.id in seen:
            continue
        seen.add(p.id)
        if p.planning_hard_rdv_date is not None:
            hard_group.append(p)
        else:
            flex_group.append(p)

    for p in sorted(hard_group, key=lambda x: x.planning_hard_rdv_date or reference_date):
        target = _clamp(p.planning_hard_rdv_date or reference_date, start_d, end_d)
        if day_load.get(target, 0) >= weights.visits_max_per_day:
            alerts[p.id] = "rdv_dur_capacity_depassee_assigne_quand_meme"
        assignments[p.id] = target
        _register_day_visit(p, target, day_load, district_count, day_centroids)

    def prio_key(x: PharmacyPlanningInputs) -> float:
        return max(
            _base_need_for_day(x, d, reference_date, weights)
            for d in horizon
        )

    flex_sorted = sorted(flex_group, key=prio_key, reverse=True)

    for p in flex_sorted:
        best_day: date | None = None
        best_score = -1e18
        for d in horizon:
            need = _base_need_for_day(p, d, reference_date, weights)
            geo_t = _geo_term(p, d, day_centroids, weights)
            dens_t = _density_bonus(p, d, district_count, weights)
            cap_penalty = 0.0
            if day_load.get(d, 0) >= weights.visits_max_per_day:
                cap_penalty = -5000.0
            total = need + geo_t + dens_t + cap_penalty
            if total > best_score:
                best_score = total
                best_day = d
        if best_day is None:
            best_day = horizon[0]
        if day_load.get(best_day, 0) >= weights.visits_max_per_day:
            alerts[p.id] = "charge_max_journaliere_glouton_fallback"
        assignments[p.id] = best_day
        _register_day_visit(p, best_day, day_load, district_count, day_centroids)

    return PlanningResult(
        assignments=assignments,
        alerts=alerts,
        diagnostics={
            "horizon": [d.isoformat() for d in horizon],
            "day_load": {k.isoformat(): v for k, v in day_load.items()},
        },
    )


def build_inputs_from_row(
    *,
    pharmacy_id: str,
    commercial_id: str,
    postal_code: str | None,
    city: str | None,
    latitude: float | None,
    longitude: float | None,
    next_visit_date_raw: str | date | None,
    planning_hard_rdv_raw: str | date | None,
    last_visit_raw: str | date | datetime | None,
    stock_status: str | None,
    visit_failed_reason: str | None,
) -> PharmacyPlanningInputs:
    return PharmacyPlanningInputs(
        id=pharmacy_id,
        commercial_id=commercial_id,
        district=district_key(postal_code, city),
        latitude=latitude,
        longitude=longitude,
        next_visit_date=_parse_date_maybe(next_visit_date_raw),
        planning_hard_rdv_date=_parse_date_maybe(planning_hard_rdv_raw),
        last_visit_date=_parse_date_maybe(last_visit_raw),
        stock_status=(stock_status or "unknown").strip().lower(),
        visit_failed_reason=(visit_failed_reason or None),
    )

