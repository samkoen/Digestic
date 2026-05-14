"""
Simulation mensuelle (par défaut **avril 2026**) : rattacher Nice / Alpes-Maritimes (+ Monaco 980xx)
au commercial Camille, puis pour chaque jour (par défaut du 2 au dernier jour du mois) :
recalcul planning + rapports synthétiques.

Les rapports sont insérés **directement en ORM** pour **ne pas** déclencher la facturation / orchestrateur BL.

Exécution depuis `backend/` :

    python scripts/simulate_april_camille_planning.py

Variables : `DATABASE_URL` (ex. dans `.env` à la racine de `backend/`).

Options utiles :
    --dry-run              : aucune écriture (assignation, planning non persistants ou dry-run API).
    --clean-april-reports  : supprime les rapports d’avril (mois demandé) pour les pharmacies ciblées avant tout.
    --skip-existing-day    : ne pas créer de rapport si un rapport existe déjà (pharmacie + jour).

Voir aussi : argparse `-h`.
"""
from __future__ import annotations

import argparse
import calendar
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import UUID

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from sqlalchemy import delete, func, or_, select, update

import app.db.models as orm
import app.db.session as db_session
from app.services.pharmacy_planning_segments_service import sync_segments_after_auto_planning_run
from app.services.planning_weights_config_service import build_combined_weights_mapping
from app.services.visit_planning_service import VisitPlanningService


def _maybe_load_dotenv() -> None:
    if load_dotenv is None:
        return
    env_path = _BACKEND / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


def nice_region_predicate(include_monaco: bool):
    pc = orm.Pharmacy.postal_code
    city_lo = func.lower(orm.Pharmacy.city)
    parts = [
        pc.startswith("06"),
        city_lo.like("%nice%"),
    ]
    if include_monaco:
        parts.append(pc.startswith("980"))
    return or_(*parts)


def resolve_commercial_id(db, first_name: str, *, allow_inactive: bool) -> UUID:
    fn = first_name.strip().lower()
    role_ok = orm.User.role == "commercial"
    q = (
        select(orm.User)
        .where(func.lower(orm.User.first_name) == fn, role_ok)
        .order_by(orm.User.email)
    )
    if not allow_inactive:
        q = q.where(orm.User.is_active.is_(True))
    rows = list(db.execute(q).scalars().all())
    if not rows:
        raise SystemExit(
            f"Aucun utilisateur trouvé : prénom « {first_name} », rôle commercial"
            + ("" if allow_inactive else ", actif uniquement.")
            + " Utilisez --allow-inactive-commercial si besoin."
        )
    if len(rows) > 1:
        emails = ", ".join(r.email for r in rows[:5])
        print(f"Attention : plusieurs « {first_name} » ({len(rows)}). On prend le premier : {emails} …")
    return rows[0].id


def clean_month_reports(db, pharmacy_ids: list[UUID], year: int, month: int) -> int:
    start = date(year, month, 1)
    last = calendar.monthrange(year, month)[1]
    end = date(year, month, last)
    stmt = delete(orm.VisitReport).where(
        orm.VisitReport.pharmacy_id.in_(pharmacy_ids),
        orm.VisitReport.visit_date >= start,
        orm.VisitReport.visit_date <= end,
    )
    res = db.execute(stmt)
    db.commit()
    return res.rowcount or 0


def build_visit_report_row(
    *,
    rng: random.Random,
    pharmacy: orm.Pharmacy,
    commercial_id: UUID,
    visit_day: date,
    skip_if_completed_prob: float,
) -> orm.VisitReport:
    stock_statuses = ["good", "low", "out_of_stock", "unknown"]
    display_statuses = ["in_place", "not_in_place", "unknown"]
    covering_statuses = ["in_place", "to_order", "unknown"]
    covering_sizes = ["S", "M", "L", "XL"]
    fail_reasons = ["pharmacy_closed", "owner_absent", "refus"]
    delivery_modes = ["normal", "normal", "normal", "deposit_sale"]
    billing_types = ["immediate", "immediate", "immediate", "monthly_recap"]

    not_done = rng.random() < skip_if_completed_prob

    payment_mode = pharmacy.payment_mode or "virement 30 jours"

    if not_done:
        return orm.VisitReport(
            pharmacy_id=pharmacy.id,
            commercial_id=commercial_id,
            visit_date=visit_day,
            visit_status="not_completed",
            visit_not_completed_reason=rng.choice(fail_reasons),
            has_deposit=False,
            bottles_deposited=0,
            free_units=0,
            stock_status=rng.choice(stock_statuses),
            display_stand_status=rng.choice(display_statuses),
            covering_status=rng.choice(covering_statuses),
            covering_size_to_order=(
                rng.choice(covering_sizes) if rng.random() < 0.25 else None
            ),
            delivery_mode="normal",
            payment_mode=payment_mode,
            notes=rng.choice(
                [
                    "Porte fermée, créneau décalé.",
                    "Pas de réponse, nouvelle tentative prévue.",
                    "Pharmacien absent.",
                    "Refus catégorique ce jour.",
                ]
            ),
            feeling_rating=None,
            synced=True,
            billing_type="immediate",
            returns_quantity=0,
            bl_reduction_percent=0,
        )

    feeling = rng.choices([1, 2, 3, 4, 5], weights=[4, 8, 14, 38, 36], k=1)[0]
    has_deposit = rng.random() < 0.42
    bottles = rng.randint(1, 14) if has_deposit else 0
    free_units = rng.randint(0, 4) if has_deposit else 0
    delivery_mode = rng.choice(delivery_modes)
    billing_type = rng.choice(billing_types)
    returns_quantity = rng.randint(0, 3) if rng.random() < 0.12 else 0
    bl_reduction_percent = float(rng.choice([0, 0, 0, 5, 10]))

    notes_pool = [
        "Bon échange, stock conforme.",
        "Demande réassort plaquette.",
        "Couverture à suivre semaine prochaine.",
        "Très satisfait du déploiement.",
        "Petit retard livraison évoqué.",
        "Place au réajustement planning.",
    ]

    return orm.VisitReport(
        pharmacy_id=pharmacy.id,
        commercial_id=commercial_id,
        visit_date=visit_day,
        visit_status="completed",
        visit_not_completed_reason=None,
        has_deposit=has_deposit,
        bottles_deposited=bottles,
        free_units=free_units,
        stock_status=rng.choice(stock_statuses),
        display_stand_status=rng.choice(display_statuses),
        covering_status=rng.choice(covering_statuses),
        covering_size_to_order=(
            rng.choice(covering_sizes) if rng.random() < 0.28 else None
        ),
        delivery_mode=delivery_mode,
        payment_mode=payment_mode,
        notes=rng.choice(notes_pool),
        feeling_rating=feeling,
        synced=True,
        billing_type=billing_type,
        returns_quantity=returns_quantity,
        bl_reduction_percent=bl_reduction_percent,
    )


def pharmacy_has_report(db, pharmacy_id: UUID, visit_day: date) -> bool:
    q = (
        select(func.count())
        .select_from(orm.VisitReport)
        .where(
            orm.VisitReport.pharmacy_id == pharmacy_id,
            orm.VisitReport.visit_date == visit_day,
        )
    )
    return int(db.scalar(q) or 0) > 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Rattache Nice / 06 (+ Monaco optionnel) à Camille et simule planning + rapports sur un mois."
    )
    p.add_argument("--commercial-first-name", default="Camille", help="Prénom du commercial (insensible à la casse).")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--month", type=int, default=4, choices=range(1, 13))
    p.add_argument("--start-day", type=int, default=2, help="Premier jour simulé (inclus).")
    p.add_argument("--end-day", type=int, default=None, help="Dernier jour simulé (inclus). Défaut : fin du mois.")
    p.add_argument("--horizon-days", type=int, default=21)
    p.add_argument("--not-completed-rate", type=float, default=0.20, help="Part de rapports « non effectuée » (~20%).")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--include-monaco", action="store_true", help="Inclure les CP commençant par 980 (Monaco).")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--clean-april-reports",
        action="store_true",
        help="Supprime tous les rapports du mois demandé pour les pharmacies géographiques ciblées.",
    )
    p.add_argument(
        "--skip-existing-day",
        action="store_true",
        help="Si un rapport existe déjà pour (pharmacie, jour), ne pas en créer un second.",
    )
    p.add_argument(
        "--allow-inactive-commercial",
        action="store_true",
        help="Autoriser la sélection d’un commercial désactivé.",
    )
    p.add_argument(
        "--planning-active-only",
        action="store_true",
        help="Limiter le recalcul planning aux pharmacies au statut « actif » (défaut : tous les statuts).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    _maybe_load_dotenv()
    db_session.get_engine()
    assert db_session.SessionLocal is not None

    year, month = args.year, args.month
    _, last_dom = calendar.monthrange(year, month)
    start_day = max(1, min(args.start_day, last_dom))
    end_day = args.end_day if args.end_day is not None else last_dom
    end_day = max(start_day, min(end_day, last_dom))

    rng = random.Random(args.seed)

    with db_session.SessionLocal() as db:
        pred = nice_region_predicate(include_monaco=args.include_monaco)
        camille_id = resolve_commercial_id(
            db,
            args.commercial_first_name,
            allow_inactive=args.allow_inactive_commercial,
        )

        base_ph_q = select(orm.Pharmacy.id).where(pred)
        base_ids = [row[0] for row in db.execute(base_ph_q).all()]
        if not base_ids:
            raise SystemExit(
                "Aucune pharmacie ne correspond au filtre géographique (06*, ville avec « nice », Monaco si activé)."
            )

        print(f"Pharmacies géographiques ciblées : {len(base_ids)}")

        if args.dry_run:
            print("[dry-run] Pas d’écriture : assignation / planning / rapports ignorés.")
            updated_would = len(base_ids)
            print(f"[dry-run] Mettrait commercial_id={camille_id} sur {updated_would} pharmacies.")
            svc = VisitPlanningService(db)
            d0 = date(year, month, start_day)
            combined_weights, _, _ = build_combined_weights_mapping(db, None)
            preview = svc.run_planning(
                reference_date=d0,
                horizon_days=args.horizon_days,
                scope_commercial_uuids=[camille_id],
                weights_overrides=combined_weights,
                dry_run=True,
                active_only=args.planning_active_only,
            )
            print(f"[dry-run] Exemple planning jour {d0.isoformat()} : planned_count={preview.get('planned_count')}")
            return

        db.execute(
            update(orm.Pharmacy)
            .where(orm.Pharmacy.id.in_(base_ids))
            .values(commercial_id=camille_id)
        )
        db.commit()
        print(f"Mis à jour commercial_id → Camille ({camille_id}) pour {len(base_ids)} pharmacies.")

        if args.clean_april_reports:
            deleted = clean_month_reports(db, base_ids, year, month)
            print(f"Nettoyage rapports du mois {year}-{month:02d} : {deleted} ligne(s) supprimée(s).")

        svc = VisitPlanningService(db)

        d = date(year, month, start_day)
        last = date(year, month, end_day)
        day_idx = 0
        while d <= last:
            day_idx += 1
            combined_weights, active_rev_id, _ = build_combined_weights_mapping(db, None)
            summary = svc.run_planning(
                reference_date=d,
                horizon_days=args.horizon_days,
                scope_commercial_uuids=[camille_id],
                weights_overrides=combined_weights,
                dry_run=False,
                active_only=args.planning_active_only,
            )
            raw_ids = summary.get("assigned_pharmacy_ids") or []
            pids_seg: list[UUID] = []
            for x in raw_ids:
                try:
                    pids_seg.append(UUID(str(x)))
                except ValueError:
                    continue
            if pids_seg:
                sync_segments_after_auto_planning_run(
                    db,
                    pharmacy_ids=pids_seg,
                    segment_valid_from=d,
                    planning_run_id=None,
                    baseline_revision_id=active_rev_id,
                    weights_override_from_request=False,
                )
            updated = summary.get("updated_count", 0)

            pharmacies = list(
                db.execute(select(orm.Pharmacy).where(orm.Pharmacy.id.in_(base_ids))).scalars().all()
            )

            reports_added = 0
            skipped_existing = 0
            for ph in pharmacies:
                if args.skip_existing_day and pharmacy_has_report(db, ph.id, d):
                    skipped_existing += 1
                    continue
                row = build_visit_report_row(
                    rng=rng,
                    pharmacy=ph,
                    commercial_id=camille_id,
                    visit_day=d,
                    skip_if_completed_prob=args.not_completed_rate,
                )
                db.add(row)
                reports_added += 1
                if row.visit_status == "completed":
                    hh = rng.randint(9, 17)
                    mm = rng.choice([0, 15, 30, 45])
                    ts = datetime.combine(d, time(hh, mm), tzinfo=timezone.utc)
                    if ph.last_visit_at is None or ph.last_visit_at < ts:
                        ph.last_visit_at = ts

            db.commit()
            print(
                f"  [{day_idx}/{end_day - start_day + 1}] {d.isoformat()} — "
                f"planning updated={updated}, rapports={reports_added}"
                + (f", ignorés (existant)={skipped_existing}" if skipped_existing else "")
            )

            d += timedelta(days=1)

    print("Terminé.")


if __name__ == "__main__":
    main()
