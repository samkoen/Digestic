"""E-mails d’alerte après planning réel : RDV « dur » vs capacité journalière max."""

from __future__ import annotations

import html as html_mod
import logging
import uuid
from collections import defaultdict
from collections.abc import Mapping
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.auth.session_roles import ADMIN
from app.domain.planning_alerts import (
    PLANNING_RDV_HARD_EMAIL_ALERT_CODES,
    humanize_planning_alert_for_email,
    split_planning_alert_tokens,
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


def _build_items_table_html(rows: list[dict]) -> str:
    if not rows:
        return "<p><em>Aucune ligne.</em></p>"
    parts = [
        "<tr><th>Pharmacie</th><th>RDV fixe</th><th>Date retenue</th>"
        "<th>Alerte</th><th>Commercial</th></tr>"
    ]
    for r in rows:
        parts.append(
            "<tr><td>{name}</td><td>{hard}</td><td>{assigned}</td>"
            "<td>{msg}</td><td>{comm}</td></tr>".format(
                name=html_mod.escape(r["pharmacy_name"]),
                hard=html_mod.escape(r["hard_rdv"]),
                assigned=html_mod.escape(r["assigned"]),
                msg=html_mod.escape(r["alert_human"]),
                comm=html_mod.escape(r["commercial_label"]),
            )
        )
    return (
        '<table border="1" cellpadding="8" cellspacing="0" '
        'style="border-collapse:collapse;font-size:14px;max-width:100%;">'
        + "".join(parts)
        + "</table>"
    )


def notify_planning_rdv_hard_alerts_maybe(
    db: Session,
    *,
    alerts: Mapping[str, str],
    assignments: Mapping[str, date],
    reference_date: date,
    horizon_days: int,
) -> None:
    """N’élève pas : journalise seulement en cas d’échec d’envoi."""
    filtered: dict[str, str] = {}
    for pid, code_raw in alerts.items():
        tokens = split_planning_alert_tokens(code_raw)
        if not tokens or not (set(tokens) & PLANNING_RDV_HARD_EMAIL_ALERT_CODES):
            continue
        filtered[pid] = code_raw

    if not filtered:
        return

    rows_all: list[dict] = []
    for pid_str, code_raw in filtered.items():
        try:
            pid = uuid.UUID(str(pid_str).strip())
        except ValueError:
            logger.warning("Alerte RDV dur : identifiant pharmacie invalide %s", pid_str)
            continue
        ph = db.get(orm.Pharmacy, pid)
        if ph is None:
            continue
        cid = getattr(ph, "commercial_id", None)
        cu = db.get(orm.User, cid) if cid else None
        comm_label = ""
        comm_email = ""
        if cu is not None:
            comm_label = f"{(cu.first_name or '').strip()} {(cu.last_name or '').strip()}".strip()
            comm_email = (cu.email or "").strip()
            if not comm_label:
                comm_label = comm_email or str(cid)
        else:
            comm_label = "(inconnu)"
        hard_dt = getattr(ph, "planning_hard_rdv_date", None)
        hard_s = hard_dt.isoformat() if hard_dt else "—"
        assigned_d = assignments.get(pid_str)
        assigned_s = assigned_d.isoformat() if assigned_d else "—"
        rows_all.append(
            {
                "pharmacy_name": ph.name or pid_str[:8],
                "hard_rdv": hard_s,
                "assigned": assigned_s,
                "alert_human": humanize_planning_alert_for_email(code_raw),
                "commercial_label": comm_label,
                "commercial_email": comm_email,
                "commercial_uuid": str(cid) if cid else "",
            }
        )

    if not rows_all:
        return

    ref_iso = reference_date.isoformat()
    mail = EmailService(db)

    by_comm: defaultdict[str, list[dict]] = defaultdict(list)
    for r in rows_all:
        by_comm[r["commercial_uuid"] or "_none_"].append(r)

    intro_comm = (
        "Suite au recalcul automatique du planning, une ou plusieurs alertes concernent vos "
        "<strong>RDV fixes</strong> (charge max un jour fermé dans votre agenda, jour non travaillé, "
        "etc.). Merci de vérifier le détail ci-dessous."
    )
    for key, sub in by_comm.items():
        if key == "_none_":
            continue
        to = (sub[0].get("commercial_email") or "").strip()
        if not to:
            logger.info(
                "Alerte RDV dur : pas d’e-mail pour le commercial (portefeuille %s) — admins notifiés seuls.",
                key,
            )
            continue
        try:
            ok = mail.send_planning_rdv_hard_capacity_alert(
                to,
                body_intro=intro_comm,
                reference_date_iso=ref_iso,
                horizon_days=horizon_days,
                items_html=_build_items_table_html(sub),
            )
            if not ok:
                logger.warning("Échec envoi alerte RDV dur au commercial %s", to)
        except Exception:
            logger.exception("Erreur envoi alerte RDV dur au commercial %s", to)

    intro_admin = (
        "Alertes RDV fixes après recalcul planning (charge journalière, jour fermé dans le calendrier du "
        "commercial…) — pharmacies concernées ci-dessous."
    )
    admin_emails = [
        (u.email or "").strip()
        for u in db.execute(
            select(orm.User).where(orm.User.role == ADMIN, orm.User.is_active.is_(True))
        ).scalars().all()
        if (u.email or "").strip()
    ]

    admin_rows = sorted(rows_all, key=lambda x: (x["commercial_label"], x["pharmacy_name"]))
    table_html = _build_items_table_html(admin_rows)

    for admin_to in sorted(set(admin_emails)):
        try:
            ok = mail.send_planning_rdv_hard_capacity_alert(
                admin_to,
                body_intro=intro_admin,
                reference_date_iso=ref_iso,
                horizon_days=horizon_days,
                items_html=table_html,
            )
            if not ok:
                logger.warning("Échec envoi alerte RDV dur à l’admin %s", admin_to)
        except Exception:
            logger.exception("Erreur envoi alerte RDV dur à l’admin %s", admin_to)
