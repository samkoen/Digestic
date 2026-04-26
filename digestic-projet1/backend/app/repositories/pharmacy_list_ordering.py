"""Tri SQL pour la liste paginée pharmacies (une fonction courte par clé)."""
from __future__ import annotations

import app.db.models as orm
from sqlalchemy.sql import Select

PharmacyT = orm.Pharmacy
UserT = orm.User
WarehouseT = orm.Warehouse


def _by_name(s: Select, asc: bool, p: PharmacyT) -> Select:
    o = p.name.asc() if asc else p.name.desc()
    return s.order_by(o)


def _by_city(s: Select, asc: bool, p: PharmacyT) -> Select:
    o = p.city.asc() if asc else p.city.desc()
    return s.order_by(o)


def _by_postal(s: Select, asc: bool, p: PharmacyT) -> Select:
    o = p.postal_code.asc() if asc else p.postal_code.desc()
    return s.order_by(o)


def _by_country(s: Select, asc: bool, p: PharmacyT) -> Select:
    o = p.country.asc() if asc else p.country.desc()
    return s.order_by(o)


def _by_commercial(
    s: Select, asc: bool, p: PharmacyT, u: UserT
) -> Select:
    o1 = u.last_name.asc() if asc else u.last_name.desc()
    o2 = u.first_name.asc() if asc else u.first_name.desc()
    return s.order_by(o1, o2)


def _by_last_visit(s: Select, asc: bool, p: PharmacyT) -> Select:
    return s.order_by(
        p.last_visit_at.isnot(None).desc(),
        p.last_visit_at.asc() if asc else p.last_visit_at.desc(),
    )


def _by_next_visit(s: Select, asc: bool, p: PharmacyT) -> Select:
    return s.order_by(
        p.next_visit_date.isnot(None).desc(),
        p.next_visit_date.asc() if asc else p.next_visit_date.desc(),
    )


def _by_created(s: Select, asc: bool, p: PharmacyT) -> Select:
    o = p.created_at.asc() if asc else p.created_at.desc()
    return s.order_by(o)


def _by_depot(
    s: Select, asc: bool, w: WarehouseT
) -> Select:
    o = w.name.asc() if asc else w.name.desc()
    return s.order_by(o)


def order_pharmacy_list(
    stmt: Select, sort_key: str, asc: bool, p: PharmacyT, u: UserT, w: WarehouseT
) -> Select:
    if sort_key == "name":
        return _by_name(stmt, asc, p)
    if sort_key == "address":
        o1 = p.address_line.asc() if asc else p.address_line.desc()
        o2 = p.postal_code.asc() if asc else p.postal_code.desc()
        o3 = p.city.asc() if asc else p.city.desc()
        return stmt.order_by(o1, o2, o3)
    if sort_key == "city":
        return _by_city(stmt, asc, p)
    if sort_key == "postalCode":
        return _by_postal(stmt, asc, p)
    if sort_key == "country":
        return _by_country(stmt, asc, p)
    if sort_key == "email":
        o = p.email.asc() if asc else p.email.desc()
        return stmt.order_by(o)
    if sort_key == "phone":
        o = p.phone.asc() if asc else p.phone.desc()
        return stmt.order_by(o)
    if sort_key == "pharmacistName":
        o = p.owner_name.asc() if asc else p.owner_name.desc()
        return stmt.order_by(o)
    if sort_key == "commercial":
        return _by_commercial(stmt, asc, p, u)
    if sort_key == "depot":
        return _by_depot(stmt, asc, w)
    if sort_key == "lastVisit":
        return _by_last_visit(stmt, asc, p)
    if sort_key == "nextVisit":
        return _by_next_visit(stmt, asc, p)
    if sort_key == "status":
        o = p.pharmacy_status.asc() if asc else p.pharmacy_status.desc()
        return stmt.order_by(o)
    if sort_key == "rib":
        o = p.has_rib.asc() if asc else p.has_rib.desc()
        return stmt.order_by(o)
    if sort_key == "paymentMode":
        o = p.payment_mode.asc() if asc else p.payment_mode.desc()
        return stmt.order_by(o)
    if sort_key == "createdAt":
        return _by_created(stmt, asc, p)
    return _by_name(stmt, True, p)
