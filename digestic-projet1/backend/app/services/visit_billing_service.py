"""Orchestration BL / stock après enregistrement d'un rapport de visite (sans facture)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import app.db.models as orm
from app.core.payment_modes import is_depot_vente
from app.db import mappers as mp
from app.domain.billing.delivery_note_number import new_digestic_bl_number
from app.models.delivery_note import DeliveryNote
from app.models.visit_report import VisitReport
from app.repositories.delivery_note_repository import DeliveryNoteRepository
from app.repositories.product_repository import get_default_billing_product_row
from app.services.billing_stock_service import (
    apply_deposit_to_pharmacy,
    apply_return_from_pharmacy,
)


class VisitBillingOrchestrator:
    def __init__(self, db: Session):
        self._db = db
        self._delivery_repo = DeliveryNoteRepository(db)

    def run_after_visit_report_persisted(self, report: VisitReport) -> None:
        returns_qty = int(getattr(report, "returns_quantity", 0) or 0)
        if returns_qty > 0 and not getattr(report, "return_source_visit_report_id", None):
            raise ValueError(
                "return_source_visit_report_id est obligatoire lorsque returns_quantity > 0"
            )

        has_shipment = bool(
            report.has_deposit and (report.bottles_deposited > 0 or report.free_units > 0)
        )
        if not has_shipment and returns_qty <= 0:
            return

        product_row = get_default_billing_product_row(self._db)
        if not product_row:
            raise ValueError(
                "Aucun produit actif en base : impossible d'appliquer le flux stock."
            )
        pid = product_row.id
        uid = mp.parse_uuid(report.commercial_id)

        if has_shipment:
            dday = mp.parse_date(report.visit_date)
            dn = DeliveryNote(
                id=str(uuid.uuid4()),
                visit_report_id=report.id,
                pharmacy_id=report.pharmacy_id,
                commercial_id=report.commercial_id,
                delivery_date=report.visit_date,
                bottles_count=report.bottles_deposited,
                free_units_quantity=report.free_units,
                is_deposit_sale=is_depot_vente(report.payment_mode),
                # Statut métier = en attente (envoi / suite) ; la validation visite est portée par validated_at.
                status="pending",
                bl_number=new_digestic_bl_number(for_date=dday),
                email_sent=False,
            )
            saved_dn = self._delivery_repo.create(dn)
            deposit_orm = self._db.get(orm.Deposit, mp.parse_uuid(saved_dn.id))
            if deposit_orm is None:
                raise RuntimeError("Dépôt non retrouvé après création")

            if report.bottles_deposited > 0:
                self._db.add(
                    orm.DepositLine(
                        deposit_id=deposit_orm.id,
                        product_id=pid,
                        quantity=report.bottles_deposited,
                    )
                )
                self._db.flush()

            ship_total = report.bottles_deposited + report.free_units
            if ship_total > 0:
                apply_deposit_to_pharmacy(
                    self._db,
                    warehouse_id=deposit_orm.warehouse_id,
                    pharmacy_id=mp.parse_uuid(report.pharmacy_id),
                    product_id=pid,
                    quantity=ship_total,
                    deposit_id=deposit_orm.id,
                    user_id=uid,
                )

            deposit_orm.status = "pending"
            deposit_orm.validated_at = datetime.now(timezone.utc)
            self._db.flush()

        if returns_qty > 0:
            p_orm = self._db.get(orm.Pharmacy, mp.parse_uuid(report.pharmacy_id))
            if not p_orm:
                raise ValueError("Pharmacie introuvable pour le retour")
            apply_return_from_pharmacy(
                self._db,
                warehouse_id=p_orm.warehouse_id,
                pharmacy_id=mp.parse_uuid(report.pharmacy_id),
                product_id=pid,
                quantity=returns_qty,
                visit_report_id=mp.parse_uuid(report.id),
                user_id=uid,
            )
            self._db.flush()
