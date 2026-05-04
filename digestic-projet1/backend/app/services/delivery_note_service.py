from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.core.payment_modes import is_depot_vente
from app.db import mappers as mp
from app.domain.billing.delivery_note_number import new_digestic_bl_number
from app.domain.billing.due_date import due_date_for_invoice
from app.domain.billing.pharmacy_reduction import (
    normalize_pharmacy_reduction_pct,
    stacked_equivalent_single_discount_pct,
    stacked_line_ht_after_reductions,
)
from app.integrations.vosfactures import get_vosfactures_invoice_issuer
from app.models.delivery_note import DeliveryNote
from app.models.invoice import Invoice
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.pharmacy_repository import PharmacyRepository
from app.repositories.product_repository import get_default_billing_product_row
from app.domain.pharmacy_notification_email import notification_email_for_pharmacy
from app.services.billing_stock_service import apply_deposit_to_pharmacy, reverse_bl_deposit_shipment
from app.services.email_service import EmailService


class DeliveryNoteService:
    """Service pour la gestion des bons de livraison."""

    def __init__(
        self,
        repository: DeliveryNoteRepository,
        invoice_repo: InvoiceRepository,
        pharmacy_repo: PharmacyRepository,
        db: Session,
    ):
        self.repository = repository
        self._invoice_repo = invoice_repo
        self._pharm_repo = pharmacy_repo
        self._db = db

    def get_all_delivery_notes(self) -> List[DeliveryNote]:
        return self.repository.find_all()

    def get_delivery_note_by_id(self, note_id: str) -> Optional[DeliveryNote]:
        return self.repository.find_by_id(note_id)

    def create_delivery_note(self, note_data: dict) -> DeliveryNote:
        note_data = dict(note_data)
        vid = note_data.get("visit_report_id")
        if vid is None or not str(vid).strip():
            raise ValueError("visit_report_id est obligatoire pour créer un bon de livraison.")
        note_data["id"] = str(uuid.uuid4())
        note = DeliveryNote.from_dict(note_data)
        return self.repository.create(note)

    def create_standalone_delivery_note_admin(self, payload: dict[str, Any]) -> DeliveryNote:
        """Bon sans rapport : réservé admin (route dédiée), même logique stock que après rapport."""
        pharmacy_id = str(payload.get("pharmacy_id") or "").strip()
        if not pharmacy_id:
            raise ValueError("pharmacy_id est obligatoire.")

        dd_raw = payload.get("delivery_date")
        if not dd_raw or not str(dd_raw).strip():
            raise ValueError("delivery_date est obligatoire.")
        dday = mp.parse_date(str(dd_raw).strip())
        delivery_date_iso = dday.isoformat()

        def _nz_int(raw: Any) -> int:
            if raw is None or isinstance(raw, bool):
                return 0
            try:
                return max(0, int(raw))
            except (TypeError, ValueError):
                try:
                    return max(0, int(float(raw)))
                except (TypeError, ValueError):
                    return 0

        bottles = _nz_int(payload.get("bottles_count"))
        free_units = _nz_int(payload.get("free_units_quantity"))
        if bottles <= 0 and free_units <= 0:
            raise ValueError(
                "Indiquez au moins une bouteille facturable ou une unité gratuite (UG)."
            )

        pharmacy = self._pharm_repo.find_by_id(pharmacy_id)
        if not pharmacy:
            raise ValueError("Pharmacie introuvable.")

        comm_raw = str(payload.get("commercial_id") or "").strip()
        commercial_id = comm_raw or str(pharmacy.commercial_id or "").strip()
        if not commercial_id:
            raise ValueError(
                "Attribuez un commercial à cette pharmacie (ou indiquez commercial_id)."
            )

        mode = str(payload.get("bl_billing_mode") or "auto").strip().lower().replace("-", "_")
        if mode in ("automatic", ""):
            mode = "auto"
        if mode not in ("auto", "depot_vente", "pending"):
            mode = "auto"
        if mode == "depot_vente":
            depot_vente_flow = True
        elif mode == "pending":
            depot_vente_flow = False
        else:
            depot_vente_flow = is_depot_vente(pharmacy.payment_mode)

        bl_status = "depot-vente" if depot_vente_flow else "pending"

        product_row = get_default_billing_product_row(self._db)
        if not product_row:
            raise ValueError(
                "Aucun produit actif en base : impossible d'appliquer le flux stock."
            )
        pid = product_row.id
        uid = mp.parse_uuid(commercial_id)

        dn = DeliveryNote(
            id=str(uuid.uuid4()),
            pharmacy_id=pharmacy_id,
            commercial_id=commercial_id,
            delivery_date=delivery_date_iso,
            bottles_count=bottles,
            free_units_quantity=free_units,
            is_deposit_sale=depot_vente_flow,
            status=bl_status,
            bl_number=new_digestic_bl_number(for_date=dday),
            email_sent=False,
            visit_report_id=None,
        )
        saved_dn = self.repository.create(dn)
        deposit_orm = self._db.get(orm.Deposit, mp.parse_uuid(saved_dn.id))
        if deposit_orm is None:
            raise RuntimeError("Dépôt non retrouvé après création")

        if bottles > 0:
            self._db.add(
                orm.DepositLine(
                    deposit_id=deposit_orm.id,
                    product_id=pid,
                    quantity=bottles,
                )
            )
            self._db.flush()

        ship_total = bottles + free_units
        if ship_total > 0:
            apply_deposit_to_pharmacy(
                self._db,
                warehouse_id=deposit_orm.warehouse_id,
                pharmacy_id=mp.parse_uuid(pharmacy_id),
                product_id=pid,
                quantity=ship_total,
                deposit_id=deposit_orm.id,
                user_id=uid,
            )

        deposit_orm.status = bl_status
        deposit_orm.validated_at = datetime.now(timezone.utc)
        self._db.flush()
        return mp.deposit_orm_to_note(deposit_orm)

    def cancel_delivery_note_admin(self, note_id: str, admin_user_id: str) -> DeliveryNote:
        """Annule un BL non facturé : statut « cancelled », retour stock si des quantités avaient été expédiées."""
        raw = str(note_id or "").strip()
        try:
            did = mp.parse_uuid(raw)
        except ValueError:
            raise ValueError("Identifiant de bon invalide.") from None

        dep = self._db.get(orm.Deposit, did)
        if not dep:
            raise ValueError("Bon de livraison introuvable.")

        st = (dep.status or "").strip().lower()
        if st == "cancelled":
            raise ValueError("Ce bon est déjà annulé.")
        if st == "fully_invoiced":
            raise ValueError("Impossible d'annuler un bon déjà entièrement facturé.")

        linked = (
            self._db.scalar(select(func.count()).select_from(orm.Invoice).where(orm.Invoice.deposit_id == did))
            or 0
        )
        if int(linked) > 0:
            raise ValueError(
                "Impossible d'annuler ce bon : une ou plusieurs factures y sont encore liées. "
                "Utilisez une procédure d'avoir ou de correction sur la ou les factures."
            )

        cancellable = {"pending", "depot-vente", "sent", "confirmed", "draft"}
        if st not in cancellable:
            raise ValueError(
                f"Annulation impossible pour le statut « {dep.status} ». Si le flux doit évoluer, contactez un admin."
            )

        qty = int(dep.bottles_count or 0) + int(dep.free_units_quantity or 0)
        product_row = get_default_billing_product_row(self._db)
        if not product_row:
            raise ValueError("Aucun produit actif en base.")

        uid_admin = mp.parse_uuid(admin_user_id)

        if qty > 0:
            reverse_bl_deposit_shipment(
                self._db,
                warehouse_id=dep.warehouse_id,
                pharmacy_id=dep.pharmacy_id,
                product_id=product_row.id,
                quantity=qty,
                deposit_id=dep.id,
                user_id=uid_admin,
            )

        for line in list(dep.lines):
            self._db.delete(line)
        dep.status = "cancelled"
        dep.bottles_count = 0
        dep.free_units_quantity = 0
        self._db.flush()
        return mp.deposit_orm_to_note(dep)

    def replace_delivery_note_with_rectified_admin(
        self,
        source_note_id: str,
        admin_user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Annule un bon puis en crée un autre dans la même transaction (bon rectificatif). Admin uniquement."""
        raw = str(source_note_id or "").strip()
        try:
            did = mp.parse_uuid(raw)
        except ValueError:
            raise ValueError("Identifiant de bon invalide.") from None

        dep = self._db.get(orm.Deposit, did)
        if not dep:
            raise ValueError("Bon de livraison introuvable.")

        pharmacy_id = str(dep.pharmacy_id)
        commercial_id_src = str(dep.commercial_id)
        prev_bl = (dep.bl_number or "").strip() or None

        pl = dict(payload)
        dd_raw = pl.get("delivery_date")
        if not dd_raw or not str(dd_raw).strip():
            raise ValueError("delivery_date est obligatoire pour le bon rectificatif.")

        def _nz(raw: Any) -> int:
            if raw is None or isinstance(raw, bool):
                return 0
            try:
                return max(0, int(raw))
            except (TypeError, ValueError):
                try:
                    return max(0, int(float(raw)))
                except (TypeError, ValueError):
                    return 0

        bottles = _nz(pl.get("bottles_count"))
        free_u = _nz(pl.get("free_units_quantity"))
        if bottles <= 0 and free_u <= 0:
            raise ValueError(
                "Indiquez au moins une bouteille facturable ou une unité gratuite pour le nouveau bon."
            )

        comm = str(pl.get("commercial_id") or "").strip() or commercial_id_src

        self.cancel_delivery_note_admin(source_note_id, admin_user_id)

        merged: dict[str, Any] = {
            "pharmacy_id": pharmacy_id,
            "commercial_id": comm,
            "delivery_date": str(dd_raw).strip(),
            "bottles_count": bottles,
            "free_units_quantity": free_u,
            "bl_billing_mode": pl.get("bl_billing_mode", "auto"),
        }
        new_note = self.create_standalone_delivery_note_admin(merged)
        out = dict(new_note.to_dict())
        out["replaced_deposit_id"] = raw
        out["replaced_bl_number"] = prev_bl
        return out

    def update_delivery_note(self, note_id: str, note_data: dict) -> Optional[DeliveryNote]:
        existing = self.repository.find_by_id(note_id)
        if not existing:
            return None

        for key, value in note_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        existing.updated_at = datetime.now().isoformat()

        return self.repository.update(note_id, existing)

    def mark_as_sent(self, note_id: str) -> Optional[DeliveryNote]:
        existing = self.repository.find_by_id(note_id)
        if not existing:
            return None
        if (existing.status or "").strip().lower() == "cancelled":
            raise ValueError("Ce bon est annulé ; impossible de le marquer comme envoyé.")
        payload = {
            "email_sent": True,
            "email_sent_at": datetime.now().isoformat(),
        }
        # Conserver le statut dépôt-vente (pas de facturation ; envoi mail ≠ passage en « envoyé » facturable).
        if (existing.status or "").strip() != "depot-vente":
            payload["status"] = "sent"
        return self.update_delivery_note(note_id, payload)

    def get_delivery_note_email_draft(self, note_id: str) -> dict[str, Any]:
        """Brouillon (destinataire + objet + HTML) depuis le modèle admin, sans envoyer ni modifier le bon."""
        dn = self.get_delivery_note_by_id(note_id)
        if not dn:
            raise ValueError("Bon de livraison introuvable.")
        if (dn.status or "").strip().lower() == "cancelled":
            raise ValueError("Bon annulé : préparation d'e-mail impossible.")

        pharmacy = self._pharm_repo.find_by_id(dn.pharmacy_id)
        if not pharmacy:
            raise ValueError("Pharmacie introuvable.")
        to_email = notification_email_for_pharmacy(pharmacy)
        if not to_email:
            raise ValueError("Aucun e-mail renseigné pour cette pharmacie.")

        svc = EmailService(self._db)
        bl_ref = (dn.bl_number or "").strip() or str(dn.id)[:13]
        subject, body_html = svc.prepare_delivery_note_email(
            pharmacy_name=pharmacy.name or "",
            bl_number=bl_ref,
            delivery_date=(dn.delivery_date or ""),
        )
        return {
            "to_email": to_email,
            "subject": subject,
            "body_html": body_html,
        }

    def send_delivery_note_email_to_pharmacy(
        self,
        note_id: str,
        *,
        subject: str | None = None,
        body_html: str | None = None,
    ) -> dict[str, Any]:
        """Envoie l’e-mail BL (modèle admin ou contenu fourni), puis marque le bon comme envoyé."""
        dn = self.get_delivery_note_by_id(note_id)
        if not dn:
            raise ValueError("Bon de livraison introuvable.")
        if (dn.status or "").strip().lower() == "cancelled":
            raise ValueError("Bon annulé : envoi d’e-mail impossible.")

        pharmacy = self._pharm_repo.find_by_id(dn.pharmacy_id)
        if not pharmacy:
            raise ValueError("Pharmacie introuvable.")
        to_email = notification_email_for_pharmacy(pharmacy)
        if not to_email:
            raise ValueError("Aucun e-mail renseigné pour cette pharmacie.")

        svc = EmailService(self._db)
        bl_ref = (dn.bl_number or "").strip() or str(dn.id)[:13]

        if subject is not None or body_html is not None:
            if subject is None or body_html is None:
                raise ValueError("Objet et corps HTML doivent être fournis ensemble.")
            ok = svc.send_custom_body(to_email, subject, body_html, kind="BL")
        else:
            ok = svc.send_delivery_note_email(
                to_email,
                pharmacy_name=pharmacy.name or "",
                bl_number=bl_ref,
                delivery_date=(dn.delivery_date or ""),
            )
        if not ok:
            raise RuntimeError("Échec lors de la préparation de l’e-mail.")

        marked = self.mark_as_sent(note_id)
        return {
            "message": f"Bon de livraison envoyé avec succès à {to_email}",
            "email": to_email,
            "delivery_note": marked.to_dict() if marked else None,
        }

    def validate_depot_vente_to_pending(self, note_id: str) -> DeliveryNote | None:
        """Passe un BL « dépôt-vente » en statut facturable (« en attente » / pending)."""
        existing = self.repository.find_by_id(note_id)
        if not existing:
            return None
        if (existing.status or "").strip().lower() == "cancelled":
            raise ValueError("Ce bon est annulé ; impossible de modifier son statut.")
        if (existing.status or "").strip() != "depot-vente":
            raise ValueError("Seuls les bons au statut dépôt-vente peuvent être validés ainsi.")
        return self.update_delivery_note(note_id, {"status": "pending"})

    def get_delivery_notes_by_pharmacy(self, pharmacy_id: str) -> List[DeliveryNote]:
        return self.repository.find_by_pharmacy(pharmacy_id)

    def get_delivery_notes_by_commercial(self, commercial_id: str) -> List[DeliveryNote]:
        return self.repository.find_by_commercial(commercial_id)

    def list_delivery_notes_paginated(
        self,
        *,
        user_role: str | None,
        user_id_str: str | None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "deliveryDate",
        order: str = "desc",
        pharmacy_id: list[str] | None = None,
        commercial_id: list[str] | None = None,
        status: str | None = None,
        delivery_date_from: str | None = None,
        delivery_date_to: str | None = None,
        deposit_id: str | None = None,
        pharmacy_name: str | None = None,
        include_archived: bool = False,
        sage_reference: str | None = None,
        is_deposit_sale: bool | None = None,
        email_sent: str | None = None,
    ) -> dict[str, Any]:
        """Liste paginée (filtres + tri) ; commercial limité à ses BL."""
        restricted: str | None = None
        if user_role == "commercial" and user_id_str:
            restricted = str(user_id_str)

        d_from: date | None = None
        d_to: date | None = None
        if delivery_date_from and str(delivery_date_from).strip():
            try:
                d_from = mp.parse_date(str(delivery_date_from).strip())
            except ValueError:
                d_from = None
        if delivery_date_to and str(delivery_date_to).strip():
            try:
                d_to = mp.parse_date(str(delivery_date_to).strip())
            except ValueError:
                d_to = None

        eff_archived = include_archived or bool(deposit_id and str(deposit_id).strip())

        pr = self.repository.search_paginated(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            pharmacy_ids=list(pharmacy_id) if pharmacy_id else None,
            commercial_ids=list(commercial_id) if commercial_id else None,
            status=status,
            delivery_date_from=d_from,
            delivery_date_to=d_to,
            deposit_id=deposit_id,
            pharmacy_name=pharmacy_name,
            include_archived=eff_archived,
            sage_reference=sage_reference,
            is_deposit_sale=is_deposit_sale,
            email_sent=email_sent,
            restricted_to_commercial_id=restricted,
        )
        ids = [str(r.deposit.id) for r in pr.items]
        sm = self._invoice_repo.invoice_summaries_by_deposit_ids(ids)
        items: list[dict[str, Any]] = []
        for r in pr.items:
            note = mp.deposit_orm_to_note(r.deposit)
            d = note.to_dict()
            d["pharmacy_name"] = r.pharmacy_name
            cname = f"{r.commercial_first_name} {r.commercial_last_name}".strip()
            d["commercial_name"] = cname
            d["linked_invoices"] = sm.get(note.id, [])
            items.append(d)
        return {
            "items": items,
            "total": pr.total,
            "page": pr.page,
            "page_size": pr.page_size,
        }

    def issue_invoice_from_delivery_note(
        self, note_id: str, bottles_to_invoice: int, amount: float
    ) -> tuple[Invoice, DeliveryNote | None]:
        """Émet la facture pour tout ou partie du BL : base locale + VosFactures (ou mock)."""
        _ = amount  # conservé pour compatibilité API ; montants calculés depuis le produit
        note = self.repository.find_by_id(note_id)
        if not note:
            raise ValueError("Bon de livraison introuvable")
        ns = (note.status or "").strip().lower()
        if ns == "cancelled":
            raise ValueError("Ce bon a été annulé ; la facturation n'est plus possible.")
        if ns == "depot-vente":
            raise ValueError("Les bons au statut dépôt-vente ne peuvent pas être facturés.")
        note_bc = int(note.bottles_count or 0)
        if bottles_to_invoice <= 0 or bottles_to_invoice > note_bc:
            raise ValueError(
                f"Quantité invalide : indiquez entre 1 et {note_bc} bouteille(s) à facturer."
            )

        product_row = get_default_billing_product_row(self._db)
        if not product_row:
            raise ValueError(
                "Aucun produit actif en base : impossible de facturer (prix / TVA)."
            )

        pharmacy = self._pharm_repo.find_by_id(note.pharmacy_id)
        if not pharmacy:
            raise ValueError("Pharmacie introuvable")

        deposit_row = self._db.get(orm.Deposit, mp.parse_uuid(note.id))
        visit_report_id_str = (
            str(deposit_row.visit_report_id) if deposit_row and deposit_row.visit_report_id else None
        )

        issue_d = date.today()
        try:
            dd = note.delivery_date
            sale_d = (
                mp.parse_date(dd)
                if dd and str(dd).strip()
                else issue_d
            )
        except ValueError:
            sale_d = issue_d
        due = due_date_for_invoice(issue_d, pharmacy.payment_mode)

        pid = product_row.id
        unit_ht = float(product_row.wholesale_unit_price)
        vat_rate = float(product_row.vat_rate)
        product_code = (product_row.code or "").strip()
        r_pct = normalize_pharmacy_reduction_pct(getattr(pharmacy, "reduction", None))
        vr_pct = 0.0
        if deposit_row and getattr(deposit_row, "visit_report_id", None):
            vrow = self._db.get(orm.VisitReport, deposit_row.visit_report_id)
            if vrow is not None:
                vr_pct = normalize_pharmacy_reduction_pct(
                    float(getattr(vrow, "bl_reduction_percent", 0) or 0)
                )

        full_paying_convert = bottles_to_invoice == note_bc
        free_qty = int(note.free_units_quantity or 0) if full_paying_convert else 0

        lines_spec: list[dict] = []
        mock_lines: list[dict] = []
        total_ht = 0.0
        total_vat = 0.0

        gross_ht = round(bottles_to_invoice * unit_ht, 4)
        lht = round(stacked_line_ht_after_reductions(gross_ht, r_pct, vr_pct), 4)
        lvat = round(lht * (vat_rate / 100.0), 4)
        total_ht += lht
        total_vat += lvat
        combined_discount = stacked_equivalent_single_discount_pct(r_pct, vr_pct)
        lines_spec.append(
            {
                "product_id": str(pid),
                "quantity": bottles_to_invoice,
                "unit_price": unit_ht,
                "vat_rate": vat_rate,
                "is_free_unit": False,
                "discount_percent": float(combined_discount) if combined_discount else 0.0,
                "line_total_ht": lht,
                "reference_unit_price_ht": None,
            }
        )
        mock_lines.append(
            {
                "label": product_row.name,
                "product_code": product_code,
                "quantity": bottles_to_invoice,
                "unit_price_ht": unit_ht,
                "vat_rate_percent": vat_rate,
                "line_ht": lht,
                "discount_percent": float(combined_discount) if combined_discount else 0.0,
                "nature": "paying",
            }
        )

        if free_qty > 0:
            lines_spec.append(
                {
                    "product_id": str(pid),
                    "quantity": free_qty,
                    "unit_price": 0.0,
                    "vat_rate": vat_rate,
                    "is_free_unit": True,
                    "discount_percent": 100.0,
                    "line_total_ht": 0.0,
                    "reference_unit_price_ht": unit_ht,
                }
            )
            mock_lines.append(
                {
                    # Même désignation que sur la facture Sage (ligne UG).
                    "label": product_row.name,
                    "product_code": product_code,
                    "quantity": free_qty,
                    "unit_price_ht": 0.0,
                    "reference_value_ht": unit_ht,
                    "vat_rate_percent": vat_rate,
                    "line_ht": 0.0,
                    "nature": "free_unit",
                }
            )

        totals = {
            "total_ht": round(total_ht, 2),
            "total_vat": round(total_vat, 2),
            "total_ttc": round(total_ht + total_vat, 2),
        }

        inv_num = f"FAC-{issue_d.strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"
        issuer = get_vosfactures_invoice_issuer()
        public_ref = (note.sage_reference or "").strip() or None
        vf = issuer.issue_vat_invoice(
            draft_invoice_number=inv_num,
            pharmacy=pharmacy,
            issue_date=issue_d,
            sale_date=sale_d,
            due_date=due,
            lines=mock_lines,
            totals=totals,
            billing_type="from_delivery_note",
            internal_deposit_id=str(note.id),
            invoice_public_reference=public_ref,
            currency=str(product_row.currency or "EUR"),
            digestic_bl_number=(note.bl_number or "").strip() or None,
        )

        inv = Invoice(
            id=str(uuid.uuid4()),
            pharmacy_id=note.pharmacy_id,
            invoice_number=vf.invoice_number or inv_num,
            amount=totals["total_ttc"],
            issue_date=issue_d.isoformat(),
            due_date=due.isoformat(),
            sale_date=sale_d.isoformat(),
            status="pending",
            deposit_id=str(note.id),
            visit_report_id=visit_report_id_str,
            billing_type="immediate",
            amount_ht=totals["total_ht"],
            amount_vat=totals["total_vat"],
            amount_ttc=totals["total_ttc"],
            external_provider=vf.provider,
            external_invoice_id=vf.external_id,
            mock_provider_payload=vf.payload,
        )
        created = self._invoice_repo.create(inv, lines=lines_spec)

        remainder = note_bc - bottles_to_invoice
        if remainder > 0:
            note.bottles_count = remainder
            note.updated_at = datetime.now().isoformat()
            next_note = self.repository.update(note.id, note)
        else:
            # Ne pas supprimer le dépôt : la FK invoices.deposit_id est ON DELETE SET NULL,
            # ce qui effacerait le lien BL ↔ facture. On clôture le bon (0 bouteilles, visible en liste).
            note.bottles_count = 0
            note.status = "fully_invoiced"
            note.updated_at = datetime.now().isoformat()
            next_note = self.repository.update(note.id, note)

        return created, next_note

    def build_delivery_note_pdf(self, note_id: str) -> tuple[bytes, str] | None:
        """PDF « Sage-like » pour le dépôt (lignes produits + totaux TVA)."""
        from app.pdf.delivery_note_pdf import build_delivery_note_pdf

        return build_delivery_note_pdf(self._db, note_id)
