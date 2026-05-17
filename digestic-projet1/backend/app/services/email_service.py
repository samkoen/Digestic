"""
Service pour l'envoi d'e-mails — contenu depuis les modèles HTML configurés en base.

Si ``BREVO_API_KEY`` et ``BREVO_SENDER_EMAIL`` sont renseignés et ``BREVO_USE_SIMULATION`` est désactivé,
les messages sont livrés via Brevo aux destinataires demandés dans l’app.

Si ``BREVO_USE_SIMULATION`` est activé (**tests**), la livraison (API ou simulation) va **exclusivement**
vers ``BREVO_SANDBOX_RECIPIENT`` (défaut : une adresse de test fixée dans ``app.integrations.brevo.config``), jamais vers l’adresse métier demandée ;
l’intention métier reste tracée dans les logs pour le débogage.
"""
from __future__ import annotations

import html as html_escape
import logging
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Sequence

from sqlalchemy.orm import Session

from app.integrations.brevo import BrevoApiError, send_transactional_html_email
from app.integrations.brevo.config import brevo_credentials_ok, brevo_force_simulation, brevo_sandbox_recipient
from app.domain.email_template_catalog import (
    TEMPLATE_DELIVERY_NOTE_SEND,
    TEMPLATE_INVOICE_SEND,
    TEMPLATE_INVOICE_UNPAID_REMINDER,
    TEMPLATE_PLANNING_RDV_HARD_CAPACITY,
)
from app.repositories.email_template_repository import EmailTemplateRepository
from app.utils.email_template_render import interpolate_template

logger = logging.getLogger(__name__)

# (octets PDF, nom de fichier — sanitisation pour les en-têtes MIME)
EmailAttachment = tuple[bytes, str]


def _sanitize_attachment_filename(name: str, fallback: str) -> str:
    s = (name or "").strip() or fallback
    safe = "".join(c if c.isalnum() or c in " ._-()" else "_" for c in s)
    return safe[:180] if safe else fallback


def _build_multipart_message(
    subject: str,
    to_email: str,
    body_html: str,
    attachments: Sequence[EmailAttachment],
) -> MIMEMultipart:
    root = MIMEMultipart("mixed")
    root["Subject"] = subject
    root["To"] = to_email
    root.attach(MIMEText(body_html, "html", "utf-8"))
    for pdf_bytes, fname in attachments:
        fn = _sanitize_attachment_filename(fname, "document.pdf")
        if not fn.lower().endswith(".pdf"):
            fn = f"{fn}.pdf"
        part = MIMEApplication(pdf_bytes, _subtype="pdf", _encoder=encoders.encode_base64)
        part.add_header("Content-Disposition", "attachment", filename=fn)
        root.attach(part)
    return root


def _money_fr(amount: float | None) -> str:
    if amount is None:
        return ""
    return f"{float(amount):.2f}".replace(".", ",")


class EmailService:
    """Construit et envoie les e-mails (Brevo si configuré, sinon simulation/logs)."""

    def __init__(self, db: Session):
        self._tpl = EmailTemplateRepository(db)

    def _render_or_fallback(
        self,
        *,
        template_key: str,
        variables: dict[str, Any],
        subject_fallback: str,
        plain_body_fallback: str,
    ) -> tuple[str, str]:
        row = self._tpl.find_by_key(template_key)
        if row is not None:
            subj = interpolate_template(row.subject_template, variables)
            body = interpolate_template(row.body_html_template, variables)
            return subj.strip(), body
        logger.warning(
            "Modèle %s absent — repli texte brut. Exécuter les migrations et le bootstrap.",
            template_key,
        )
        plain = interpolate_template(plain_body_fallback, variables)
        subj_fb = interpolate_template(subject_fallback, variables)
        escaped = html_escape.escape(plain)
        wrapped = (
            '<div style="font-family:system-ui,sans-serif;font-size:15px;line-height:1.5;color:#222;">'
            f'<pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{escaped}</pre></div>'
        )
        return subj_fb.strip(), wrapped

    def prepare_invoice_email(
        self,
        *,
        pharmacy_name: str,
        invoice_number: str,
        invoice_amount: float | None,
        invoice_date: str | None,
        due_date: str | None,
    ) -> tuple[str, str]:
        ctx = {
            "pharmacy_name": pharmacy_name or "",
            "invoice_number": invoice_number or "",
            "invoice_amount": _money_fr(invoice_amount),
            "invoice_date": invoice_date or "",
            "due_date": due_date or "",
        }
        subj_fallback = "Facture {{ invoice_number }} — {{ pharmacy_name }}"
        body_fallback = (
            "Bonjour,\n\n"
            "Veuillez trouver ci-joint la facture {{ invoice_number }} "
            "pour {{ pharmacy_name }}, d'un montant de {{ invoice_amount }} €.\n\n"
            "Date d'émission : {{ invoice_date }} — échéance : {{ due_date }}"
        )
        return self._render_or_fallback(
            template_key=TEMPLATE_INVOICE_SEND,
            variables=ctx,
            subject_fallback=subj_fallback,
            plain_body_fallback=body_fallback,
        )

    def send_invoice_email(
        self,
        to_email: str,
        *,
        pharmacy_name: str,
        invoice_number: str,
        invoice_amount: float | None,
        invoice_date: str | None,
        due_date: str | None,
        attachments: Sequence[EmailAttachment] | None = None,
    ) -> bool:
        subject, html = self.prepare_invoice_email(
            pharmacy_name=pharmacy_name,
            invoice_number=invoice_number,
            invoice_amount=invoice_amount,
            invoice_date=invoice_date,
            due_date=due_date,
        )
        return self._log_send(
            to_email, subject, html, kind="facture", attachments=attachments or ()
        )

    def prepare_delivery_note_email(
        self,
        *,
        pharmacy_name: str,
        bl_number: str | None,
        delivery_date: str | None,
    ) -> tuple[str, str]:
        ctx = {
            "pharmacy_name": pharmacy_name or "",
            "bl_number": bl_number or "—",
            "delivery_date": delivery_date or "",
        }
        subj_fallback = "Bon de livraison — {{ pharmacy_name }}"
        body_fallback = (
            "Bonjour,\n\n"
            "Veuillez trouver ci-joint le bon de livraison pour {{ pharmacy_name }} "
            "(réf. {{ bl_number }}), date {{ delivery_date }}."
        )
        return self._render_or_fallback(
            template_key=TEMPLATE_DELIVERY_NOTE_SEND,
            variables=ctx,
            subject_fallback=subj_fallback,
            plain_body_fallback=body_fallback,
        )

    def send_delivery_note_email(
        self,
        to_email: str,
        *,
        pharmacy_name: str,
        bl_number: str | None,
        delivery_date: str | None,
        attachments: Sequence[EmailAttachment] | None = None,
    ) -> bool:
        subject, html = self.prepare_delivery_note_email(
            pharmacy_name=pharmacy_name,
            bl_number=bl_number,
            delivery_date=delivery_date,
        )
        return self._log_send(to_email, subject, html, kind="BL", attachments=attachments or ())

    def send_custom_body(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        *,
        kind: str,
        attachments: Sequence[EmailAttachment] | None = None,
    ) -> bool:
        if not (subject or "").strip():
            raise ValueError("L'objet est obligatoire.")
        if not (body_html or "").strip():
            raise ValueError("Le corps du message est obligatoire.")
        return self._log_send(
            to_email, subject.strip(), body_html, kind=kind, attachments=attachments or ()
        )

    def send_invoice_unpaid_reminder_email(
        self,
        to_email: str,
        *,
        pharmacy_name: str,
        invoice_number: str,
        invoice_amount: float | None,
        invoice_date: str | None,
        due_date: str | None,
        days_overdue: int | str,
    ) -> bool:
        ctx = {
            "pharmacy_name": pharmacy_name or "",
            "invoice_number": invoice_number or "",
            "invoice_amount": _money_fr(invoice_amount),
            "invoice_date": invoice_date or "",
            "due_date": due_date or "",
            "days_overdue": str(days_overdue),
        }
        subj_fallback = "Rappel — facture {{ invoice_number }}"
        body_fallback = (
            "Bonjour,\n\n"
            "La facture {{ invoice_number }} pour {{ pharmacy_name }} "
            "({{ invoice_amount }} €), émise le {{ invoice_date }}, "
            "avec échéance {{ due_date }}, présente encore un solde ouvert "
            "({{ days_overdue }} jour(s) de retard).\n\n"
            "Merci de régulariser la situation."
        )
        subject, html = self._render_or_fallback(
            template_key=TEMPLATE_INVOICE_UNPAID_REMINDER,
            variables=ctx,
            subject_fallback=subj_fallback,
            plain_body_fallback=body_fallback,
        )
        return self._log_send(to_email, subject, html, kind="rappel_facture_impayée", attachments=())

    def send_planning_rdv_hard_capacity_alert(
        self,
        to_email: str,
        *,
        body_intro: str,
        reference_date_iso: str,
        horizon_days: int,
        items_html: str,
    ) -> bool:
        ctx = {
            "body_intro": body_intro,
            "reference_date": reference_date_iso,
            "horizon_days": str(int(horizon_days)),
            "items_html": items_html,
        }
        subject_fb = "[Digestic] Alerte planning — RDV fixe / charge journalière"
        plain_fb = (
            "{{ body_intro }}\n\nRéférence planning : {{ reference_date }} — "
            "horizon {{ horizon_days }} jour(s).\n\n(détail des pharmacies dans la version HTML)"
        )
        subject, html = self._render_or_fallback(
            template_key=TEMPLATE_PLANNING_RDV_HARD_CAPACITY,
            variables=ctx,
            subject_fallback=subject_fb,
            plain_body_fallback=plain_fb,
        )
        return self._log_send(
            (to_email or "").strip(),
            subject,
            html,
            kind="planning_rdv_dur",
            attachments=(),
        )

    def _log_send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        *,
        kind: str,
        attachments: Sequence[EmailAttachment] = (),
    ) -> bool:
        try:
            att_list = list(attachments) if attachments else ()
            sandbox = brevo_force_simulation()
            orig_to = (to_email or "").strip()
            recipient = brevo_sandbox_recipient().strip() if sandbox else orig_to

            use_brevo_api = brevo_credentials_ok()

            if use_brevo_api:
                try:
                    resp = send_transactional_html_email(
                        to_email=recipient,
                        subject=subject,
                        html_content=body_html,
                        attachments=list(att_list) if att_list else None,
                    )
                    mid = None
                    if isinstance(resp, dict):
                        mid = resp.get("messageId") or resp.get("message_id")
                    pj_note = ", ".join(_sanitize_attachment_filename(fn, "file.pdf") for _, fn in att_list)
                    mode = "Brevo sandbox (destinataire forcé)" if sandbox else "Brevo"
                    extra = ""
                    if sandbox and orig_to.lower() != recipient.lower():
                        extra = f"\n  (demande app : {orig_to} → livré uniquement sur le sandbox ci-dessous)\n"
                    print(
                        f"\n--- E-mail envoyé via {mode} ({kind})\n"
                        f"{extra}"
                        f"  Destinataire : {recipient}\n"
                        f"  Objet        : {subject}\n"
                        f"  Pièces joint.: {pj_note or 'aucune'}\n"
                        f"  Message ID   : {mid or '—'}\n"
                        "---\n",
                        flush=True,
                    )
                    logger.info(
                        "[email:brevo %s] orig=%s -> %s sandbox=%s messageId=%s attachments=%s",
                        kind,
                        orig_to,
                        recipient,
                        sandbox,
                        mid,
                        [fn for _, fn in att_list],
                    )
                    return True
                except BrevoApiError as e:
                    logger.error("[email:brevo] Échec (%s %s→%s): %s", kind, orig_to, recipient, e)
                    return False

            excerpt = body_html[:1200] + (" …[tronqué]" if len(body_html) > 1200 else "")
            att_lines = "".join(
                f"  Pièce jointe  : {_sanitize_attachment_filename(fn, 'fichier.pdf')} ({len(data)} o)\n"
                for data, fn in att_list
            )
            if not att_list:
                att_lines = "  Pièces jointes : aucune\n"

            mime_msg = _build_multipart_message(subject, recipient, body_html, list(att_list))

            sandbox_note = (
                "\n  (demande dans l’app : " + orig_to + " → simulation uniquement pour le sandbox ci-dessus)\n"
                if sandbox and orig_to.lower() != recipient.lower()
                else ""
            )
            mode_label = "Simulation sandbox" if sandbox else "Simulation — Brevo non configuré"
            print(
                f"\n--- {mode_label} e-mail ({kind}) — pas d’API Brevo —\n"
                f"{sandbox_note}"
                f"  Destinataire : {recipient}\n"
                f"  Objet        : {subject}\n"
                f"{att_lines}"
                f"  Corps HTML   :\n{excerpt}\n"
                f"  MIME (approx. {len(mime_msg.as_bytes())} o)\n"
                "---\n",
                flush=True,
            )
            logger.info("[email:simulation %s] orig=%s -> %s", kind, orig_to, recipient)
            logger.info("Sujet: %s", subject)
            logger.info("Pièces jointes: %s", [a[1] for a in att_list])
            logger.info("Corps HTML: %s", body_html[:2000])
            return True
        except Exception as e:
            logger.error("Erreur lors de la préparation de l'e-mail: %s", e)
            return False
