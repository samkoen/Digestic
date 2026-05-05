"""
Service pour l'envoi d'e-mails — contenu depuis les modèles HTML configurés en base.
Pour l'instant envoi simulé (journalisation).
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

from app.domain.email_template_catalog import (
    TEMPLATE_DELIVERY_NOTE_SEND,
    TEMPLATE_INVOICE_SEND,
    TEMPLATE_INVOICE_UNPAID_REMINDER,
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
    """Construit puis envoie (simulation) les e-mails à partir des modèles admin."""

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
            excerpt = body_html[:1200] + (" …[tronqué]" if len(body_html) > 1200 else "")
            att_lines = "".join(
                f"  Pièce jointe  : {_sanitize_attachment_filename(fn, 'fichier.pdf')} ({len(data)} o)\n"
                for data, fn in attachments
            )
            if not attachments:
                att_lines = "  Pièces jointes : aucune\n"

            mime_msg = _build_multipart_message(subject, to_email, body_html, list(attachments))
            # MIME prêt pour SMTP ; pour l’instant journalisation uniquement

            print(
                f"\n--- Simulation e-mail ({kind}) — pas de SMTP —\n"
                f"  Destinataire : {to_email}\n"
                f"  Objet        : {subject}\n"
                f"{att_lines}"
                f"  Corps HTML   :\n{excerpt}\n"
                f"  MIME (approx. {len(mime_msg.as_bytes())} o)\n"
                "---\n",
                flush=True,
            )
            logger.info("[email:%s] -> %s", kind, to_email)
            logger.info("Sujet: %s", subject)
            logger.info("Pièces jointes: %s", [a[1] for a in attachments])
            logger.info("Corps HTML: %s", body_html[:2000])
            return True
        except Exception as e:
            logger.error("Erreur lors de la préparation de l'e-mail: %s", e)
            return False
