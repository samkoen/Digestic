"""Facturation : visites (type facturation, retours), dépôt/BL, facture étendue, récap, avoir, paiement.

Revision ID: j7k8_billing_visit_flow
Revises: i5j6_pharmacy_view_city
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "j7k8_billing_visit_flow"
down_revision: Union[str, None] = "i5j6_pharmacy_view_city"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visit_reports",
        sa.Column(
            "billing_type",
            sa.String(32),
            nullable=False,
            server_default="immediate",
        ),
    )
    op.add_column(
        "visit_reports",
        sa.Column("returns_quantity", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "visit_reports",
        sa.Column("return_source_visit_report_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_visit_reports_return_source",
        "visit_reports",
        "visit_reports",
        ["return_source_visit_report_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_visit_reports_billing_type",
        "visit_reports",
        "billing_type IN ('immediate', 'monthly_recap')",
    )

    op.add_column(
        "deposits",
        sa.Column("free_units_quantity", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("invoices", sa.Column("deposit_id", UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("visit_report_id", UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("sale_date", sa.Date(), nullable=True))
    op.add_column(
        "invoices",
        sa.Column(
            "invoice_billing_type",
            sa.String(32),
            nullable=True,
        ),
    )
    op.add_column("invoices", sa.Column("amount_ht", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("amount_vat", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("amount_ttc", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("external_provider", sa.String(32), nullable=True))
    op.add_column("invoices", sa.Column("external_invoice_id", sa.String(128), nullable=True))
    op.add_column("invoices", sa.Column("mock_provider_payload", JSONB, nullable=True))
    op.create_foreign_key(
        "fk_invoices_deposit",
        "invoices",
        "deposits",
        ["deposit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_invoices_visit_report",
        "invoices",
        "visit_reports",
        ["visit_report_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invoices_deposit_id", "invoices", ["deposit_id"])
    op.create_index("ix_invoices_visit_report_id", "invoices", ["visit_report_id"])

    op.add_column(
        "invoice_lines",
        sa.Column("is_free_unit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.add_column("invoice_lines", sa.Column("line_total_ht", sa.Numeric(12, 4), nullable=True))
    op.add_column(
        "invoice_lines",
        sa.Column("reference_unit_price_ht", sa.Numeric(12, 4), nullable=True),
    )

    op.create_table(
        "billing_recap_slices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "visit_report_id",
            UUID(as_uuid=True),
            sa.ForeignKey("visit_reports.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "pharmacy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "deposit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("deposits.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("year_month", sa.String(7), nullable=False, index=True),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_billing_recap_slices_pharmacy_month",
        "billing_recap_slices",
        ["pharmacy_id", "year_month"],
    )

    op.create_table(
        "credit_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pharmacy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("credit_note_number", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("amount_ttc", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_ht", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount_vat", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="issued"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("external_provider", sa.String(32), nullable=True),
        sa.Column("external_credit_note_id", sa.String(128), nullable=True),
        sa.Column("mock_provider_payload", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "credit_note_lines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "credit_note_id",
            UUID(as_uuid=True),
            sa.ForeignKey("credit_notes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_free_unit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "payments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pharmacy_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pharmacies.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("payment_mode", sa.String(64), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "invoice_payment_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "payment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("payments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "invoice_id",
            UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("invoice_payment_allocations")
    op.drop_table("payments")
    op.drop_table("credit_note_lines")
    op.drop_table("credit_notes")
    op.drop_index("ix_billing_recap_slices_pharmacy_month", table_name="billing_recap_slices")
    op.drop_table("billing_recap_slices")

    op.drop_column("invoice_lines", "reference_unit_price_ht")
    op.drop_column("invoice_lines", "line_total_ht")
    op.drop_column("invoice_lines", "discount_percent")
    op.drop_column("invoice_lines", "is_free_unit")

    op.drop_index("ix_invoices_visit_report_id", table_name="invoices")
    op.drop_index("ix_invoices_deposit_id", table_name="invoices")
    op.drop_constraint("fk_invoices_visit_report", "invoices", type_="foreignkey")
    op.drop_constraint("fk_invoices_deposit", "invoices", type_="foreignkey")
    op.drop_column("invoices", "mock_provider_payload")
    op.drop_column("invoices", "external_invoice_id")
    op.drop_column("invoices", "external_provider")
    op.drop_column("invoices", "amount_ttc")
    op.drop_column("invoices", "amount_vat")
    op.drop_column("invoices", "amount_ht")
    op.drop_column("invoices", "invoice_billing_type")
    op.drop_column("invoices", "sale_date")
    op.drop_column("invoices", "visit_report_id")
    op.drop_column("invoices", "deposit_id")

    op.drop_column("deposits", "free_units_quantity")

    op.drop_constraint("fk_visit_reports_return_source", "visit_reports", type_="foreignkey")
    op.drop_constraint("ck_visit_reports_billing_type", "visit_reports", type_="check")
    op.drop_column("visit_reports", "return_source_visit_report_id")
    op.drop_column("visit_reports", "returns_quantity")
    op.drop_column("visit_reports", "billing_type")
