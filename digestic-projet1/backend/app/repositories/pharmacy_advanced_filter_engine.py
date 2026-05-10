"""Traduction définition filtre avancé pharmacies → prédicats SQL (liste paginée).

Payload attendu (après sanitisation) ::
  { "combine": "and" | "or", "conditions": [ { "subject", "field", "op", "value" }, ... ] }

- subject ``pharmacy`` : colonnes de la pharmacie.
- subject ``invoice`` : EXISTS sur ``invoices`` liées.
- subject ``delivery_note`` : EXISTS sur ``deposits`` (BL).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, exists, func, or_, select

import app.db.models as orm

OPS_ALL = frozenset({"=", "!=", "<", ">", "<=", ">="})
OPS_EQ = frozenset({"=", "!="})

ALLOWED_INVOICE_STATUS = frozenset(
    {"pending", "overdue", "paid", "credited", "cancelled"}
)
ALLOWED_DEPOSIT_STATUS = frozenset(
    {
        "pending",
        "validated",
        "sent",
        "confirmed",
        "fully_invoiced",
        "draft",
        "depot-vente",
        "cancelled",
    }
)


def sanitize_pharmacy_advanced_filter_payload(raw: Any) -> dict[str, Any]:
    """Retourne ``{ combine, conditions }`` sûr pour stockage et exécution."""
    combine = "and"
    if isinstance(raw, dict):
        cmb = str(raw.get("combine") or "and").strip().lower()
        if cmb == "or":
            combine = "or"
        conds_in = raw.get("conditions")
    else:
        conds_in = None
    out_conds: list[dict[str, Any]] = []
    if isinstance(conds_in, list):
        for c in conds_in:
            sc = _sanitize_one_condition(c)
            if sc is not None:
                out_conds.append(sc)
    return {"combine": combine, "conditions": out_conds}


def _sanitize_one_condition(c: Any) -> dict[str, Any] | None:
    if not isinstance(c, dict):
        return None
    subject = str(c.get("subject") or "").strip().lower()
    field = str(c.get("field") or "").strip().lower()
    op = str(c.get("op") or "").strip()
    if op not in OPS_ALL:
        return None
    val = c.get("value")
    if val is None:
        return None
    val_s = str(val).strip()

    if subject == "pharmacy":
        allowed = {
            "pharmacy_status": "str_eq",
            "city": "str_eq",
            "postal_code": "str_eq",
            "next_visit_date": "date",
            "created_at": "date",
        }
        kind = allowed.get(field)
        if not kind:
            return None
        if kind == "str_eq" and op not in OPS_EQ:
            return None
        if kind == "date" and op not in OPS_ALL:
            return None
        if not val_s:
            return None
        if kind == "date" and _parse_date(val_s) is None:
            return None
        return {"subject": "pharmacy", "field": field, "op": op, "value": val_s}

    if subject == "invoice":
        allowed = {
            "status": "inv_st",
            "issue_date": "date",
            "due_date": "date",
            "days_overdue": "int",
            "amount": "float",
        }
        kind = allowed.get(field)
        if not kind:
            return None
        if kind == "inv_st" and op not in OPS_EQ:
            return None
        if kind == "date" and op not in OPS_ALL:
            return None
        if kind in ("int", "float") and op not in OPS_ALL:
            return None
        if kind == "inv_st" and val_s.lower() not in ALLOWED_INVOICE_STATUS:
            return None
        if kind == "date" and _parse_date(val_s) is None:
            return None
        if kind == "int" and _parse_int(val_s) is None:
            return None
        if kind == "float" and _parse_float(val_s) is None:
            return None
        return {"subject": "invoice", "field": field, "op": op, "value": val_s}

    if subject == "delivery_note":
        allowed = {
            "status": "dep_st",
            "delivery_date": "date",
            "bottles_count": "int",
        }
        kind = allowed.get(field)
        if not kind:
            return None
        if kind == "dep_st" and op not in OPS_EQ:
            return None
        if kind == "date" and op not in OPS_ALL:
            return None
        if kind == "int" and op not in OPS_ALL:
            return None
        if kind == "dep_st" and val_s.lower() not in ALLOWED_DEPOSIT_STATUS:
            return None
        if kind == "date" and _parse_date(val_s) is None:
            return None
        if kind == "int" and _parse_int(val_s) is None:
            return None
        return {"subject": "delivery_note", "field": field, "op": op, "value": val_s}

    return None


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s.strip()[:10])
    except ValueError:
        return None


def _parse_int(s: str) -> int | None:
    try:
        return int(s.strip())
    except ValueError:
        return None


def _parse_float(s: str) -> float | None:
    try:
        return float(s.strip().replace(",", "."))
    except ValueError:
        return None


def _cmp_op_sql(lhs, op: str, rhs):
    if op == "=":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == "<":
        return lhs < rhs
    if op == ">":
        return lhs > rhs
    if op == "<=":
        return lhs <= rhs
    if op == ">=":
        return lhs >= rhs
    return None


def apply_advanced_pharmacy_filter_conditions(
    conds: list,
    p_tbl: Any,
    payload: dict[str, Any] | None,
) -> None:
    if not payload or not isinstance(payload, dict):
        return
    combine = str(payload.get("combine") or "and").lower()
    if combine not in ("and", "or"):
        combine = "and"
    conditions = payload.get("conditions")
    if not isinstance(conditions, list):
        return
    predicates: list = []
    for c in conditions:
        if not isinstance(c, dict):
            continue
        pred = _condition_to_predicate(p_tbl, c)
        if pred is not None:
            predicates.append(pred)
    if not predicates:
        return
    if combine == "or":
        conds.append(or_(*predicates))
    else:
        conds.extend(predicates)


def _condition_to_predicate(p_tbl: Any, c: dict[str, Any]) -> Any:
    subject = str(c.get("subject") or "").strip().lower()
    field = str(c.get("field") or "").strip().lower()
    op = str(c.get("op") or "").strip()
    val_s = str(c.get("value") or "").strip()
    if subject == "pharmacy":
        return _pharmacy_predicate(p_tbl, field, op, val_s)
    if subject == "invoice":
        return _invoice_exists_predicate(p_tbl, field, op, val_s)
    if subject == "delivery_note":
        return _deposit_exists_predicate(p_tbl, field, op, val_s)
    return None


def _pharmacy_predicate(p_tbl: Any, field: str, op: str, val_s: str) -> Any:
    if field == "pharmacy_status":
        lhs = func.lower(p_tbl.pharmacy_status)
        rhs = val_s.strip().lower()
        return _cmp_op_sql(lhs, op, rhs)
    if field == "city":
        lhs = func.lower(p_tbl.city)
        rhs = val_s.strip().lower()
        return _cmp_op_sql(lhs, op, rhs)
    if field == "postal_code":
        lhs = func.lower(p_tbl.postal_code)
        rhs = val_s.strip().lower()
        return _cmp_op_sql(lhs, op, rhs)
    if field == "next_visit_date":
        d = _parse_date(val_s)
        if d is None:
            return None
        return _cmp_op_sql(p_tbl.next_visit_date, op, d)
    if field == "created_at":
        d = _parse_date(val_s)
        if d is None:
            return None
        lhs = func.date(func.timezone("UTC", p_tbl.created_at))
        return _cmp_op_sql(lhs, op, d)
    return None


def _invoice_inner_parts(field: str, op: str, val_s: str) -> list | None:
    inv = orm.Invoice
    parts: list = []
    if field == "status":
        lhs = func.lower(inv.status)
        rhs = val_s.strip().lower()
        e = _cmp_op_sql(lhs, op, rhs)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "issue_date":
        d = _parse_date(val_s)
        if d is None:
            return None
        e = _cmp_op_sql(inv.issue_date, op, d)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "due_date":
        d = _parse_date(val_s)
        if d is None:
            return None
        e = _cmp_op_sql(inv.due_date, op, d)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "days_overdue":
        n = _parse_int(val_s)
        if n is None:
            return None
        e = _cmp_op_sql(inv.days_overdue, op, n)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "amount":
        x = _parse_float(val_s)
        if x is None:
            return None
        e = _cmp_op_sql(inv.amount, op, x)
        if e is None:
            return None
        parts.append(e)
        return parts
    return None


def _invoice_exists_predicate(p_tbl: Any, field: str, op: str, val_s: str) -> Any:
    inv = orm.Invoice
    inner = _invoice_inner_parts(field, op, val_s)
    if inner is None:
        return None
    all_parts = [inv.pharmacy_id == p_tbl.id, *inner]
    return exists(select(1).select_from(inv).where(and_(*all_parts)))


def _deposit_inner_parts(field: str, op: str, val_s: str) -> list | None:
    dep = orm.Deposit
    parts: list = []
    if field == "status":
        lhs = func.lower(dep.status)
        rhs = val_s.strip().lower()
        e = _cmp_op_sql(lhs, op, rhs)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "delivery_date":
        d = _parse_date(val_s)
        if d is None:
            return None
        e = _cmp_op_sql(dep.delivery_date, op, d)
        if e is None:
            return None
        parts.append(e)
        return parts
    if field == "bottles_count":
        n = _parse_int(val_s)
        if n is None:
            return None
        e = _cmp_op_sql(dep.bottles_count, op, n)
        if e is None:
            return None
        parts.append(e)
        return parts
    return None


def _deposit_exists_predicate(p_tbl: Any, field: str, op: str, val_s: str) -> Any:
    dep = orm.Deposit
    inner = _deposit_inner_parts(field, op, val_s)
    if inner is None:
        return None
    all_parts = [dep.pharmacy_id == p_tbl.id, *inner]
    return exists(select(1).select_from(dep).where(and_(*all_parts)))
