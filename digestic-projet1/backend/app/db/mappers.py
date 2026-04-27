"""Conversions ORM <-> modèles domaine (dataclasses) pour l'API."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any

import app.db.models as orm
from app.models.commercial_material import CommercialMaterial
from app.models.delivery_note import DeliveryNote
from app.models.invoice import Invoice
from app.models.pharmacy import Pharmacy
from app.models.product import Product
from app.models.user import User
from app.models.visit import Visit
from app.models.visit_report import VisitReport


def parse_uuid(value: str | uuid.UUID | None) -> uuid.UUID:
    if value is None:
        raise ValueError("identifiant manquant")
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def parse_date(value: str | date | datetime | None) -> date:
    if value is None:
        raise ValueError("date manquante")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if "T" in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    return date.fromisoformat(s[:10])


def parse_datetime_iso(dt: datetime | None) -> str:
    if dt is None:
        return datetime.now().isoformat()
    if dt.tzinfo is not None:
        return dt.isoformat()
    return dt.replace(tzinfo=None).isoformat()


def _payment_to_api(mode: str) -> str:
    from app.core.payment_modes import payment_mode_for_api

    return payment_mode_for_api(mode)


def user_orm_to_domain(row: orm.User) -> User:
    return User(
        id=str(row.id),
        email=row.email,
        first_name=row.first_name,
        last_name=row.last_name,
        role=row.role,
        phone=row.phone,
        is_active=row.is_active,
        created_at=parse_datetime_iso(row.created_at) if row.created_at else None,
        updated_at=parse_datetime_iso(row.updated_at) if row.updated_at else None,
    )


def product_orm_to_domain(row: orm.Product) -> Product:
    return Product(
        id=str(row.id),
        code=row.code,
        ean=getattr(row, "ean", None),
        name=row.name,
        description=row.description,
        wholesale_unit_price=float(row.wholesale_unit_price),
        currency=row.currency or "EUR",
        vat_rate=float(row.vat_rate),
        units_per_carton=int(row.units_per_carton),
        is_default_for_billing=bool(getattr(row, "is_default_for_billing", False)),
        is_active=row.is_active,
        created_at=parse_datetime_iso(row.created_at) if row.created_at else None,
        updated_at=parse_datetime_iso(row.updated_at) if row.updated_at else None,
    )


def pharm_orm_to_domain(p: orm.Pharmacy, warehouse: orm.Warehouse | None = None) -> Pharmacy:
    w = warehouse
    if w is None and getattr(p, "warehouse", None) is not None:
        w = p.warehouse
    return Pharmacy(
        id=str(p.id),
        name=p.name,
        address=p.address_line,
        city=p.city,
        postal_code=p.postal_code,
        warehouse_id=str(p.warehouse_id),
        depot_name=(w.name if w else None),
        depot_type=(w.depot_type if w else None),
        country=p.country,
        email=p.email,
        phone=p.phone,
        latitude=p.latitude,
        longitude=p.longitude,
        pharmacist_name=p.owner_name,
        # owner_* peut être vide alors que email/phone de la pharmacie sont renseignés (ex. import Sage)
        pharmacist_email=(p.owner_email or p.email or None),
        pharmacist_phone=(p.owner_phone or p.phone or None),
        rib=p.rib,
        status=(p.pharmacy_status or "actif"),
        commercial_id=str(p.commercial_id) if p.commercial_id else None,
        last_visit_at=parse_datetime_iso(p.last_visit_at) if p.last_visit_at else None,
        next_visit_date=p.next_visit_date.isoformat() if p.next_visit_date else None,
        photo_url=p.photo_url,
        payment_mode=_payment_to_api(p.payment_mode),
        created_at=parse_datetime_iso(p.created_at) if p.created_at else None,
        updated_at=parse_datetime_iso(p.updated_at) if p.updated_at else None,
    )


def visit_orm_to_domain(v: orm.Visit) -> Visit:
    st = v.scheduled_time.strftime("%H:%M") if v.scheduled_time else None
    return Visit(
        id=str(v.id),
        pharmacy_id=str(v.pharmacy_id),
        commercial_id=str(v.commercial_id),
        scheduled_date=v.scheduled_date.isoformat() if v.scheduled_date else "",
        scheduled_time=st,
        status=v.status,
        notes=v.notes,
        created_at=parse_datetime_iso(v.created_at) if v.created_at else None,
        updated_at=parse_datetime_iso(v.updated_at) if v.updated_at else None,
    )


def report_orm_to_domain(r: orm.VisitReport) -> VisitReport:
    nvd = r.next_visit_date.isoformat() if r.next_visit_date else None
    return VisitReport(
        id=str(r.id),
        pharmacy_id=str(r.pharmacy_id),
        commercial_id=str(r.commercial_id),
        visit_date=r.visit_date.isoformat() if r.visit_date else "",
        visit_id=str(r.visit_id) if r.visit_id else None,
        visit_status=r.visit_status,
        visit_not_completed_reason=r.visit_not_completed_reason,
        has_deposit=r.has_deposit,
        bottles_deposited=r.bottles_deposited,
        free_units=r.free_units,
        stock_status=r.stock_status,
        display_stand_status=r.display_stand_status,
        covering_status=r.covering_status,
        covering_size_to_order=r.covering_size_to_order,
        next_visit_date=nvd,
        expected_return_iso_year=r.expected_return_iso_year,
        expected_return_iso_week=r.expected_return_iso_week,
        voice_note_url=r.voice_note_url,
        photo_note_url=r.photo_note_url,
        video_note_url=r.video_note_url,
        delivery_mode=r.delivery_mode,
        payment_mode=_payment_to_api(r.payment_mode),
        notes=r.notes,
        synced=r.synced,
        billing_type=getattr(r, "billing_type", None) or "immediate",
        returns_quantity=int(getattr(r, "returns_quantity", 0) or 0),
        return_source_visit_report_id=(
            str(r.return_source_visit_report_id)
            if getattr(r, "return_source_visit_report_id", None)
            else None
        ),
        created_at=parse_datetime_iso(r.created_at) if r.created_at else None,
        updated_at=parse_datetime_iso(r.updated_at) if r.updated_at else None,
    )


def deposit_orm_to_note(d: orm.Deposit) -> DeliveryNote:
    at = d.email_sent_at
    at_s: str | None = at.isoformat() if at is not None else None
    return DeliveryNote(
        id=str(d.id),
        visit_report_id=str(d.visit_report_id),
        pharmacy_id=str(d.pharmacy_id),
        commercial_id=str(d.commercial_id),
        delivery_date=d.delivery_date.isoformat() if d.delivery_date else "",
        bottles_count=d.bottles_count,
        free_units_quantity=int(getattr(d, "free_units_quantity", 0) or 0),
        is_deposit_sale=d.is_deposit_sale,
        status=d.status,
        sage_reference=d.reference_external,
        email_sent=d.email_sent,
        email_sent_at=at_s,
        created_at=parse_datetime_iso(d.created_at) if d.created_at else None,
        updated_at=parse_datetime_iso(d.updated_at) if d.updated_at else None,
    )


def invoice_orm_to_domain(inv: orm.Invoice) -> Invoice:
    pd: str | None = inv.payment_date.isoformat() if inv.payment_date else None
    sd: str | None = inv.sale_date.isoformat() if getattr(inv, "sale_date", None) else None
    mock_payload = getattr(inv, "mock_provider_payload", None)
    return Invoice(
        id=str(inv.id),
        pharmacy_id=str(inv.pharmacy_id),
        invoice_number=inv.invoice_number,
        amount=float(inv.amount),
        issue_date=inv.issue_date.isoformat() if inv.issue_date else "",
        due_date=inv.due_date.isoformat() if inv.due_date else "",
        status=inv.status,
        payment_date=pd,
        sage_reference=inv.reference_external,
        deposit_id=str(inv.deposit_id) if getattr(inv, "deposit_id", None) else None,
        visit_report_id=str(inv.visit_report_id) if getattr(inv, "visit_report_id", None) else None,
        sale_date=sd,
        billing_type=getattr(inv, "invoice_billing_type", None),
        amount_ht=float(inv.amount_ht) if getattr(inv, "amount_ht", None) is not None else None,
        amount_vat=float(inv.amount_vat) if getattr(inv, "amount_vat", None) is not None else None,
        amount_ttc=float(inv.amount_ttc) if getattr(inv, "amount_ttc", None) is not None else None,
        external_provider=getattr(inv, "external_provider", None),
        external_invoice_id=getattr(inv, "external_invoice_id", None),
        mock_provider_payload=dict(mock_payload) if mock_payload else None,
        days_overdue=inv.days_overdue,
        created_at=parse_datetime_iso(inv.created_at) if inv.created_at else None,
        updated_at=parse_datetime_iso(inv.updated_at) if inv.updated_at else None,
    )


def material_orm_to_domain(m: orm.CommercialMaterial) -> CommercialMaterial:
    return CommercialMaterial(
        id=str(m.id),
        name=m.name,
        type=m.type,
        file_path=m.file_path,
        file_url=m.file_url,
        description=m.description,
        version=m.version,
        is_active=m.is_active,
        created_at=parse_datetime_iso(m.created_at) if m.created_at else None,
        updated_at=parse_datetime_iso(m.updated_at) if m.updated_at else None,
    )


# --- Saisie API (dict) -> champs base ---


def normalize_payment_mode_to_db(v: str | None) -> str:
    from app.core.payment_modes import normalize_pharmacy_payment_mode

    return normalize_pharmacy_payment_mode(v)


def parse_time_hm(value: str | None) -> time | None:
    if not value:
        return None
    p = str(value).strip()
    if len(p) == 5 and p[2] == ":":
        h, m_ = p.split(":", 1)
        return time(int(h), int(m_))
    if "T" in p:
        return datetime.fromisoformat(p.replace("Z", "+00:00")).time()
    return None
