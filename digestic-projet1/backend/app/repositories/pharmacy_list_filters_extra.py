"""Filtres supplémentaires (texte) sur la liste pharmacies — fonctions courtes."""
from __future__ import annotations

from collections.abc import Sequence

import app.db.models as orm
from sqlalchemy import String, cast, func, or_
from sqlalchemy.sql import ColumnElement

PharmT = orm.Pharmacy


def _ilike_pat(q: str) -> str:
    t = (q or "").strip()
    for ch in ("\\", "%", "_"):
        t = t.replace(ch, "\\" + ch)
    return f"%{t}%" if t else "%"


def _append_str(
    conds: list[ColumnElement[bool]], col, raw: str | None
) -> None:
    if not raw or not str(raw).strip():
        return
    pat = _ilike_pat(str(raw))
    conds.append(col.ilike(pat, escape="\\"))


def _normalize_postal_code_terms(
    postal_code: str | Sequence[str] | None,
) -> list[str] | None:
    if postal_code is None:
        return None
    if isinstance(postal_code, str):
        t = postal_code.strip()
        return [t] if t else None
    out: list[str] = []
    seen: set[str] = set()
    for x in postal_code:
        t = str(x).strip() if x is not None else ""
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out or None


def _append_ilike_any(
    conds: list[ColumnElement[bool]], col, terms: list[str] | None
) -> None:
    if not terms:
        return
    parts = [col.ilike(_ilike_pat(t), escape="\\") for t in terms]
    if len(parts) == 1:
        conds.append(parts[0])
    else:
        conds.append(or_(*parts))


def _normalize_exact_str_terms(
    raw: str | Sequence[str] | None,
) -> list[str] | None:
    """Valeurs exactes (ex. modes de paiement), sans ILIKE — plusieurs = OU (IN)."""
    if raw is None:
        return None
    if isinstance(raw, str):
        t = raw.strip()
        return [t] if t else None
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        t = str(x).strip() if x is not None else ""
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out or None


def _append_in_terms(
    conds: list[ColumnElement[bool]], col, terms: list[str] | None
) -> None:
    if not terms:
        return
    conds.append(col.in_(terms))


def apply_extra_pharmacy_filters(
    conds: list[ColumnElement[bool]],
    p: PharmT,
    *,
    city: str | Sequence[str] | None = None,
    postal_code: str | Sequence[str] | None = None,
    country: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    owner_name: str | None = None,
    payment_mode: str | Sequence[str] | None = None,
    created: str | None = None,
    depot: str | None = None,
    warehouse: orm.Warehouse | None = None,
) -> None:
    if warehouse is not None:
        _append_str(conds, warehouse.name, depot)
    _append_ilike_any(conds, p.city, _normalize_postal_code_terms(city))
    _append_ilike_any(conds, p.postal_code, _normalize_postal_code_terms(postal_code))
    _append_str(conds, p.country, country)
    _append_str(conds, p.email, email)
    _append_str(conds, p.phone, phone)
    _append_str(conds, p.owner_name, owner_name)
    _append_in_terms(
        conds, p.payment_mode, _normalize_exact_str_terms(payment_mode)
    )
    if not created or not str(created).strip():
        return
    pat = _ilike_pat(str(created))
    conds.append(
        or_(
            func.to_char(p.created_at, "DD/MM/YYYY").ilike(pat, escape="\\"),
            func.to_char(p.created_at, "YYYY-MM-DD").ilike(pat, escape="\\"),
            cast(p.created_at, String).ilike(pat, escape="\\"),
        )
    )


