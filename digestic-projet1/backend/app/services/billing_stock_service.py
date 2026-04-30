"""Mouvements de stock liés au BL (dépôt chez la pharmacie / retour)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.db.models as orm


def _ensure_warehouse_stock_row(
    db: Session, warehouse_id: uuid.UUID, product_id: uuid.UUID
) -> orm.WarehouseStock:
    ws = db.execute(
        select(orm.WarehouseStock).where(
            orm.WarehouseStock.warehouse_id == warehouse_id,
            orm.WarehouseStock.product_id == product_id,
        )
    ).scalar_one_or_none()
    if ws:
        return ws
    ws = orm.WarehouseStock(warehouse_id=warehouse_id, product_id=product_id, quantity=0)
    db.add(ws)
    db.flush()
    return ws


def _ensure_pharmacy_balance_row(
    db: Session, pharmacy_id: uuid.UUID, product_id: uuid.UUID
) -> orm.PharmacyProductBalance:
    bal = db.execute(
        select(orm.PharmacyProductBalance).where(
            orm.PharmacyProductBalance.pharmacy_id == pharmacy_id,
            orm.PharmacyProductBalance.product_id == product_id,
        )
    ).scalar_one_or_none()
    if bal:
        return bal
    bal = orm.PharmacyProductBalance(
        pharmacy_id=pharmacy_id, product_id=product_id, quantity_deposited=0, quantity_invoiced=0
    )
    db.add(bal)
    db.flush()
    return bal


def apply_deposit_to_pharmacy(
    db: Session,
    *,
    warehouse_id: uuid.UUID,
    pharmacy_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
    deposit_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> None:
    if quantity <= 0:
        return
    ws = _ensure_warehouse_stock_row(db, warehouse_id, product_id)
    wh = db.get(orm.Warehouse, warehouse_id)
    # L'écran Dépôts alimente `warehouses.quantity` ; les sorties BL décrémentent
    # `warehouse_stocks`. Si une ligne produit est en retard (ex. 1) alors que le dépôt
    # affiche 2000, aligner — uniquement si ce dépôt n'a qu'une ligne stock (monoproduit),
    # pour ne pas gonfler une référence quand plusieurs produits partagent le même total.
    n_stock_lines = int(
        db.execute(
            select(func.count())
            .select_from(orm.WarehouseStock)
            .where(orm.WarehouseStock.warehouse_id == warehouse_id)
        ).scalar_one()
        or 0
    )
    if wh is not None:
        wh_q = int(wh.quantity)
        if n_stock_lines <= 1 and ws.quantity < wh_q:
            ws.quantity = wh_q
            db.flush()
        elif ws.quantity == 0 and wh_q > 0:
            ws.quantity = wh_q
            db.flush()

    if ws.quantity < quantity:
        raise ValueError(
            f"Stock dépôt insuffisant (disponible {ws.quantity}, demandé {quantity})"
        )
    ws.quantity -= quantity
    if wh is not None:
        wh.quantity = max(0, int(wh.quantity) - quantity)
    bal = _ensure_pharmacy_balance_row(db, pharmacy_id, product_id)
    bal.quantity_deposited += quantity
    db.add(
        orm.StockMovement(
            movement_type="bl_outbound",
            warehouse_id=warehouse_id,
            pharmacy_id=pharmacy_id,
            product_id=product_id,
            quantity=quantity,
            ref_table="deposits",
            ref_id=deposit_id,
            created_by=user_id,
        )
    )


def apply_return_from_pharmacy(
    db: Session,
    *,
    warehouse_id: uuid.UUID,
    pharmacy_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
    visit_report_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> None:
    if quantity <= 0:
        return
    bal = _ensure_pharmacy_balance_row(db, pharmacy_id, product_id)
    if bal.quantity_deposited < quantity:
        raise ValueError(
            "Quantité retournée supérieure au solde déposé en pharmacie pour ce produit"
        )
    bal.quantity_deposited -= quantity
    ws = _ensure_warehouse_stock_row(db, warehouse_id, product_id)
    ws.quantity += quantity
    wh = db.get(orm.Warehouse, warehouse_id)
    if wh is not None:
        wh.quantity = int(wh.quantity) + quantity
    db.add(
        orm.StockMovement(
            movement_type="return_from_pharmacy",
            warehouse_id=warehouse_id,
            pharmacy_id=pharmacy_id,
            product_id=product_id,
            quantity=quantity,
            ref_table="visit_reports",
            ref_id=visit_report_id,
            created_by=user_id,
        )
    )
