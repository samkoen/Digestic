"""
Modèles ORM (PostgreSQL). Migrations gérées par Alembic.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="commercial")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        CheckConstraint(
            "depot_type IN ('central', 'secondaire')",
            name="ck_warehouses_depot_type",
        ),
        CheckConstraint("quantity >= 0", name="ck_warehouses_quantity_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    depot_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="secondaire"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    stocks: Mapped[list["WarehouseStock"]] = relationship(back_populates="warehouse")


class DepotTransfer(Base):
    """Mouvement de quantité d'un dépôt vers un autre (audit)."""

    __tablename__ = "depot_transfers"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_depot_transfer_qty_positive"),
        CheckConstraint(
            "from_warehouse_id <> to_warehouse_id",
            name="ck_depot_transfer_different_warehouses",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    from_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    from_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped["Warehouse"] = relationship(foreign_keys=[to_warehouse_id])
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_user_id])


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    code: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    ean: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    wholesale_unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    units_per_carton: Mapped[int] = mapped_column(Integer, nullable=False)
    is_default_for_billing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    __table_args__ = (CheckConstraint("units_per_carton > 0", name="ck_product_units_per_carton"),)

    stocks: Mapped[list["WarehouseStock"]] = relationship(back_populates="product")
    price_history: Mapped[list["ProductPriceHistory"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductPriceHistory(Base):
    __tablename__ = "product_price_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    new_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    product: Mapped["Product"] = relationship(back_populates="price_history")
    user: Mapped["User | None"] = relationship()


class WarehouseStock(Base):
    __tablename__ = "warehouse_stocks"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_warehouse_product_stock"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    warehouse: Mapped["Warehouse"] = relationship(back_populates="stocks")
    product: Mapped["Product"] = relationship(back_populates="stocks")


class PharmacyGroup(Base):
    __tablename__ = "pharmacy_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    membership_links: Mapped[list["PharmacyGroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Pharmacy(Base):
    __tablename__ = "pharmacies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_secondary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    commercial_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    has_rib: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rib: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_mode: Mapped[str] = mapped_column(
        String(80), nullable=False, default="virement 30 jours"
    )
    reduction_percent: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    gocardless_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gocardless_mandate_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pharmacy_status: Mapped[str] = mapped_column(
        String(32), default="actif", nullable=False
    )
    last_visit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    warehouse: Mapped["Warehouse"] = relationship()
    commercial: Mapped["User"] = relationship()
    group_links: Mapped[list["PharmacyGroupMember"]] = relationship(
        back_populates="pharmacy", cascade="all, delete-orphan"
    )
    pharmacy_comments: Mapped[list["PharmacyComment"]] = relationship(
        back_populates="pharmacy", cascade="all, delete-orphan"
    )


class PharmacyComment(Base):
    __tablename__ = "pharmacy_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    pharmacy: Mapped["Pharmacy"] = relationship(back_populates="pharmacy_comments")


class PharmacyGroupMember(Base):
    """Affectation d'une pharmacie à un groupe (N–N)."""

    __tablename__ = "pharmacy_group_members"
    __table_args__ = (UniqueConstraint("pharmacy_id", "group_id", name="uq_pharmacy_group"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacy_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )

    pharmacy: Mapped["Pharmacy"] = relationship(back_populates="group_links")
    group: Mapped["PharmacyGroup"] = relationship(back_populates="membership_links")


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commercial_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    pharmacy: Mapped["Pharmacy"] = relationship()
    commercial: Mapped["User"] = relationship()
    visit_reports: Mapped[list["VisitReport"]] = relationship(back_populates="visit")


class VisitReport(Base):
    __tablename__ = "visit_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    visit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("visits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commercial_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    visit_status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    visit_not_completed_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    has_deposit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bottles_deposited: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    display_stand_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    covering_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    covering_size_to_order: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_return_iso_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_return_iso_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_note_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_note_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_note_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_mode: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    payment_mode: Mapped[str] = mapped_column(
        String(64), default="virement 30 jours", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    billing_type: Mapped[str] = mapped_column(
        String(32), default="immediate", nullable=False
    )
    returns_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bl_reduction_percent: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    return_source_visit_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("visit_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "billing_type IN ('immediate', 'monthly_recap')",
            name="ck_visit_reports_billing_type",
        ),
    )

    visit: Mapped["Visit | None"] = relationship(back_populates="visit_reports")
    deposits: Mapped[list["Deposit"]] = relationship(back_populates="visit_report")


class Deposit(Base):
    """Dépôt / bon (évolution de delivery_note), lignes par produit dans deposit_lines."""

    __tablename__ = "deposits"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    visit_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("visit_reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    commercial_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    delivery_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    is_deposit_sale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reference_external: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bl_number: Mapped[str | None] = mapped_column(String(48), nullable=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Total bouteilles (flux legacy aligné sur l'ancien modèle delivery_note) ; complété par deposit_lines
    bottles_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    free_units_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    visit_report: Mapped["VisitReport | None"] = relationship(back_populates="deposits")
    lines: Mapped[list["DepositLine"]] = relationship(
        back_populates="deposit", cascade="all, delete-orphan"
    )


class DepositLine(Base):
    __tablename__ = "deposit_lines"
    __table_args__ = (
        UniqueConstraint("deposit_id", "product_id", name="uq_deposit_product"),
        CheckConstraint("quantity > 0", name="ck_deposit_line_qty_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    deposit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deposits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    deposit: Mapped["Deposit"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()


class PharmacyProductBalance(Base):
    __tablename__ = "pharmacy_product_balances"
    __table_args__ = (
        UniqueConstraint("pharmacy_id", "product_id", name="uq_pharmacy_product_balance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity_deposited: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_invoiced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    pharmacy: Mapped["Pharmacy"] = relationship()
    product: Mapped["Product"] = relationship()


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pharmacy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_table: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    deposit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deposits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    visit_report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("visit_reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_billing_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount_ht: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_vat: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_ttc: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_external: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mock_provider_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    days_overdue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    pharmacy: Mapped["Pharmacy"] = relationship()
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_free_unit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    line_total_ht: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    reference_unit_price_ht: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()


class BillingRecapSlice(Base):
    """Morceau de facturation pour facture récapitulative de fin de mois (hors facture finale)."""

    __tablename__ = "billing_recap_slices"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    visit_report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("visit_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deposit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deposits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    year_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CreditNote(Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        CheckConstraint(
            "credit_scope IN ('full', 'partial')",
            name="ck_credit_notes_credit_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    credit_note_number: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_ttc: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    amount_ht: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_vat: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="issued", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_credit_note_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    mock_provider_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    credit_scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default="full", server_default="full"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    lines: Mapped[list["CreditNoteLine"]] = relationship(
        back_populates="credit_note", cascade="all, delete-orphan"
    )


class CreditNoteLine(Base):
    __tablename__ = "credit_note_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    credit_note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credit_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    vat_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_free_unit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_invoice_line_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoice_lines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    credit_note: Mapped["CreditNote"] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()
    source_invoice_line: Mapped["InvoiceLine | None"] = relationship()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    pharmacy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pharmacies.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_mode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InvoicePaymentAllocation(Base):
    __tablename__ = "invoice_payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)


class CommercialMaterial(Base):
    __tablename__ = "commercial_materials"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AppTableViewSetting(Base):
    """Colonnes visibles (ordre) pour un type de tableau, éditable par admin."""

    __tablename__ = "app_table_view_settings"
    __table_args__ = (UniqueConstraint("view_key", name="uq_app_table_view_settings_view_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    view_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    visible_column_keys: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class SavedListFilter(Base):
    """Préréglages de filtres liste (pharmacies, factures, …) par utilisateur."""

    __tablename__ = "saved_list_filters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    view_key: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EmailTemplate(Base):
    """Modèles d’e-mail (HTML) éditables par l’admin. Clé fonctionnelle = template_key."""

    __tablename__ = "email_templates"
    __table_args__ = (UniqueConstraint("template_key", name="uq_email_templates_template_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=_uuid
    )
    template_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_html_template: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by: Mapped["User | None"] = relationship(foreign_keys=[updated_by_user_id])


