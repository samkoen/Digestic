"""Données référentielles minimales (ex. entrepôt par défaut)."""
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

import app.db.models as orm
from app.domain.email_template_catalog import EMAIL_TEMPLATE_CATALOG

DEFAULT_WAREHOUSE_NAME = "Entrepot principal"

_WRAPPER = (
    '<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
    'color:#1a1a1a;line-height:1.5;font-size:15px;max-width:640px;">'
    "\n{s}\n<p style=\"color:#444;margin-top:1.6em;font-size:14px;\">Cordialement,<br/>"
    "L'équipe Digestic</p>\n</div>"
)


def _default_subject_and_body_html(entry_key: str) -> tuple[str, str]:
    if entry_key == "delivery_note_send":
        inner = """<p>Bonjour,</p>
<p>Veuillez trouver ci-joint le bon de livraison pour <strong>{{ pharmacy_name }}</strong>,
référence <strong>{{ bl_number }}</strong>.</p>
<p>Date de livraison&nbsp;: {{ delivery_date }}</p>"""
        return ("Bon de livraison — {{ pharmacy_name }}", _WRAPPER.format(s=inner))
    if entry_key == "invoice_send":
        inner = """<p>Bonjour,</p>
<p>Veuillez trouver ci-joint la facture <strong>{{ invoice_number }}</strong> pour
<strong>{{ pharmacy_name }}</strong>, d'un montant de <strong>{{ invoice_amount }}</strong>&nbsp;€.</p>
<p>Date d'émission&nbsp;: {{ invoice_date }} — échéance&nbsp;: {{ due_date }}</p>"""
        return ("Facture {{ invoice_number }} — {{ pharmacy_name }}", _WRAPPER.format(s=inner))
    if entry_key == "invoice_unpaid_reminder":
        inner = """<p>Bonjour,</p>
<p>Nous nous permettons de vous rappeler que la facture <strong>{{ invoice_number }}</strong>
pour <strong>{{ pharmacy_name }}</strong>, d'un montant de <strong>{{ invoice_amount }}</strong>&nbsp;€,
n'est pas réglée à ce jour.</p>
<p>Date d'émission&nbsp;: {{ invoice_date }} — échéance&nbsp;: {{ due_date }}
— retard&nbsp;: <strong>{{ days_overdue }}</strong>&nbsp;jour(s).</p>
<p>Merci de procéder au règlement ou de nous contacter en cas de difficulté.</p>"""
        return ("Rappel — facture {{ invoice_number }} impayée", _WRAPPER.format(s=inner))
    if entry_key == "planning_rdv_hard_capacity_alert":
        inner = """<p>{{ body_intro }}</p>
<p><strong>Référence planning</strong> : {{ reference_date }} — horizon <strong>{{ horizon_days }}</strong> jour(s).</p>
{{ items_html }}"""
        return ("[Digestic] Alerte planning — RDV fixe / charge journalière", _WRAPPER.format(s=inner))
    inner = "<p>{{ message }}</p>"
    return ("Message Digestic", _WRAPPER.format(s=inner))


def get_or_create_default_warehouse_id(db: Session) -> uuid.UUID:
    w = db.execute(
        select(orm.Warehouse).where(orm.Warehouse.name == DEFAULT_WAREHOUSE_NAME)
    ).scalar_one_or_none()
    if w is not None:
        return w.id
    w = orm.Warehouse(
        name=DEFAULT_WAREHOUSE_NAME,
        country="FR",
        is_active=True,
        depot_type="central",
        quantity=0,
    )
    db.add(w)
    db.flush()
    return w.id


def ensure_builtin_email_templates(db: Session) -> None:
    """Insère les lignes catalogue si absentes (sans écraser les personnalisations admin)."""
    for entry in EMAIL_TEMPLATE_CATALOG:
        subj, body = _default_subject_and_body_html(entry.key)
        stmt = pg_insert(orm.EmailTemplate).values(
            template_key=entry.key,
            subject_template=subj,
            body_html_template=body,
        ).on_conflict_do_nothing(index_elements=["template_key"])
        db.execute(stmt)
