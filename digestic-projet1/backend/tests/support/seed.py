"""Jeux de données minimaux pour scénarios BL / facturation (tests d'intégration)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.core.security import hash_password
from app.db import bootstrap


@dataclass(frozen=True)
class BlIntegrationSeed:
    admin_email: str
    admin_password: str
    admin_id: uuid.UUID
    commercial_id: uuid.UUID
    pharmacy_id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID


def seed_bl_integration_world(db: Session) -> BlIntegrationSeed:
    """
    Insère entrepôt, stock, produit de facturation, commercial, admin et pharmacie rattachée.
    Les lignes sont visibles dans la transaction du test (rollback en fin de cas).
    """
    suffix = uuid.uuid4().hex[:8]
    admin_email = f"admin-{suffix}@test.digestic.local"
    commercial_email = f"commercial-{suffix}@test.digestic.local"
    pwd = "TestSuite-Bl-2026!"

    wid = bootstrap.get_or_create_default_warehouse_id(db)
    warehouse = db.get(orm.Warehouse, wid)
    if warehouse is None:
        raise RuntimeError("Entrepôt par défaut introuvable après bootstrap")
    warehouse.quantity = max(int(warehouse.quantity or 0), 100_000)

    product = orm.Product(
        code=f"TST-{suffix}",
        name=f"Produit test {suffix}",
        wholesale_unit_price=10.0,
        currency="EUR",
        vat_rate=20.0,
        units_per_carton=1,
        is_default_for_billing=True,
        is_active=True,
    )
    db.add(product)
    db.flush()

    stock = db.execute(
        select(orm.WarehouseStock).where(
            orm.WarehouseStock.warehouse_id == wid,
            orm.WarehouseStock.product_id == product.id,
        )
    ).scalar_one_or_none()
    if stock is None:
        stock = orm.WarehouseStock(
            warehouse_id=wid,
            product_id=product.id,
            quantity=50_000,
        )
        db.add(stock)
    else:
        stock.quantity = max(int(stock.quantity or 0), 50_000)
    db.flush()

    commercial_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    db.add(
        orm.User(
            id=commercial_id,
            email=commercial_email,
            password_hash=hash_password(pwd),
            first_name="Com",
            last_name="Mercial",
            role="commercial",
            is_active=True,
        )
    )
    db.add(
        orm.User(
            id=admin_id,
            email=admin_email,
            password_hash=hash_password(pwd),
            first_name="Ad",
            last_name="Min",
            role="admin",
            is_active=True,
        )
    )
    db.flush()

    pharmacy = orm.Pharmacy(
        id=uuid.uuid4(),
        name=f"Pharmacie test {suffix}",
        address_line="1 rue Test",
        city="Paris",
        postal_code="75001",
        country="FR",
        phone="0102030405",
        email=f"pharma-{suffix}@test.digestic.local",
        warehouse_id=wid,
        commercial_id=commercial_id,
        payment_mode="virement 30 jours",
    )
    db.add(pharmacy)
    db.flush()

    return BlIntegrationSeed(
        admin_email=admin_email,
        admin_password=pwd,
        admin_id=admin_id,
        commercial_id=commercial_id,
        pharmacy_id=pharmacy.id,
        warehouse_id=wid,
        product_id=product.id,
    )
