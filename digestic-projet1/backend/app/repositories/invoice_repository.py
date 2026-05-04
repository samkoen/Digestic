import uuid
from collections import defaultdict
from datetime import date
from typing import Any, Optional

from sqlalchemy import Date, Integer, and_, cast, func, literal, or_, select, String, union_all
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session, aliased

import app.db.models as orm
from app.db import mappers as mp
from app.domain.invoice_table_columns import INVOICE_SORT_KEYS
from app.models.invoice import Invoice
from app.pagination import PageResult, offset_for_page, normalize_page_input


def _invoice_tuple_to_api_dict(model: Invoice, pname: str | None, bln: str | None, has_cn: bool) -> dict[str, Any]:
    d = model.to_dict()
    d["row_kind"] = "invoice"
    d["pharmacy_name"] = pname or ""
    d["bl_number"] = (str(bln).strip() if bln else "") or ""
    d["has_credit_notes"] = bool(has_cn)
    d["external_credit_note_id"] = None
    d["source_invoice_id"] = None
    return d


def _union_row_to_api_dict(row: Any) -> dict[str, Any]:
    kind = row.row_kind
    doc = row.doc_number
    amt = float(row.amount or 0)
    raw_issue = getattr(row, "issue_date")
    raw_due = getattr(row, "due_date")
    issue = raw_issue.isoformat() if hasattr(raw_issue, "isoformat") else (str(raw_issue) if raw_issue else "")
    due = raw_due.isoformat() if hasattr(raw_due, "isoformat") else (str(raw_due) if raw_due else "")
    blv = getattr(row, "bl_number", None)
    bln = (str(blv).strip() if blv else "") or ""
    deposit = getattr(row, "deposit_id", None)
    ext_inv = getattr(row, "external_invoice_id", None)
    ext_cn = getattr(row, "external_credit_note_id", None)
    src_sid = getattr(row, "source_invoice_id", None)
    raw_pd = getattr(row, "payment_date", None)
    pay_d = (
        raw_pd.isoformat()
        if raw_pd is not None and hasattr(raw_pd, "isoformat")
        else (str(raw_pd) if raw_pd else None)
    )
    return {
        "row_kind": kind,
        "id": str(row.id),
        "pharmacy_id": str(row.pharmacy_id),
        "invoice_number": str(doc) if doc is not None else "",
        "amount": amt,
        "issue_date": issue,
        "due_date": due,
        "status": str(row.status) if row.status is not None else "",
        "payment_date": pay_d,
        "sage_reference": None,
        "deposit_id": str(deposit) if deposit is not None else None,
        "visit_report_id": None,
        "sale_date": None,
        "billing_type": None,
        "amount_ht": None,
        "amount_vat": None,
        "amount_ttc": amt,
        "external_provider": row.external_provider,
        "external_invoice_id": str(ext_inv) if ext_inv else None,
        "mock_provider_payload": None,
        "days_overdue": int(row.days_overdue or 0),
        "created_at": None,
        "updated_at": None,
        "pharmacy_name": str(row.pharmacy_name or ""),
        "bl_number": bln,
        "has_credit_notes": kind == "credit_note",
        "external_credit_note_id": str(ext_cn) if ext_cn else None,
        "source_invoice_id": str(src_sid) if src_sid else None,
    }


def _order_clause_union(sort: str, order: str, u: Any) -> Any:
    desc_ = (order or "asc").lower() == "desc"
    s = sort if sort in INVOICE_SORT_KEYS else "issueDate"
    if s == "pharmacyName":
        col = u.c.pharmacy_name
    elif s == "issueDate":
        col = u.c.issue_date
    elif s == "dueDate":
        col = u.c.due_date
    elif s == "invoiceNumber":
        col = u.c.doc_number
    elif s == "amount":
        col = u.c.amount
    elif s == "status":
        col = u.c.status
    elif s == "blNumber":
        col = u.c.bl_number
    else:
        col = u.c.days_overdue
    ob = col.desc() if desc_ else col.asc()
    if s == "blNumber":
        ob = ob.nulls_last()
    return ob


def _order_clause(
    sort: str,
    order: str,
    i: type[orm.Invoice],
    p: type[orm.Pharmacy],
    d: type[orm.Deposit],
):
    """Tri SQL (camelCase -> colonnes, avec pharmacie et dépôt)."""
    desc_ = (order or "asc").lower() == "desc"
    s = sort if sort in INVOICE_SORT_KEYS else "issueDate"
    col: Any
    if s == "pharmacyName":
        col = p.name
    elif s == "issueDate":
        col = i.issue_date
    elif s == "dueDate":
        col = i.due_date
    elif s == "invoiceNumber":
        col = i.invoice_number
    elif s == "amount":
        col = i.amount
    elif s == "status":
        col = i.status
    elif s == "blNumber":
        col = d.bl_number
    else:
        col = i.days_overdue
    ob = col.desc() if desc_ else col.asc()
    if s == "blNumber":
        ob = ob.nulls_last()
    return ob


def invoice_line_ht_total(li: orm.InvoiceLine) -> float:
    """HT total ligne facture Digestic (pour répartition avoir partiel)."""
    if getattr(li, "is_free_unit", False):
        return 0.0
    if li.line_total_ht is not None:
        return round(float(li.line_total_ht), 4)
    qty = float(li.quantity or 0)
    unit = float(li.unit_price or 0)
    d = float(li.discount_percent or 0)
    return round(qty * unit * (1.0 - d / 100.0), 4)


def invoice_line_rounded_ttc(li: orm.InvoiceLine) -> float:
    ht = invoice_line_ht_total(li)
    vat_r = float(li.vat_rate or 0)
    return round(ht * (1.0 + vat_r / 100.0), 2)


class InvoiceRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[Invoice]:
        rows = self._db.execute(select(orm.Invoice)).scalars().all()
        return [mp.invoice_orm_to_domain(r) for r in rows]

    def credited_quantities_per_invoice_line(self, invoice_uuid: uuid.UUID) -> dict[uuid.UUID, int]:
        cnl = orm.CreditNoteLine
        cn = orm.CreditNote
        q = (
            select(cnl.source_invoice_line_id, func.coalesce(func.sum(cnl.quantity), 0))
            .join(cn, cnl.credit_note_id == cn.id)
            .where(cn.source_invoice_id == invoice_uuid)
            .where(cnl.source_invoice_line_id.is_not(None))
            .group_by(cnl.source_invoice_line_id)
        )
        rows = self._db.execute(q).all()
        out: dict[uuid.UUID, int] = {}
        for sid, summed in rows:
            if sid is None:
                continue
            out[sid] = int(summed or 0)
        return out

    def list_invoice_lines_for_credit(self, invoice_id: str) -> list[dict[str, Any]]:
        try:
            iid = mp.parse_uuid(invoice_id)
        except ValueError:
            return []
        credited = self.credited_quantities_per_invoice_line(iid)
        ili = orm.InvoiceLine
        pr = orm.Product
        stmt = (
            select(ili, pr.name, pr.code)
            .join(pr, ili.product_id == pr.id)
            .where(ili.invoice_id == iid)
            .order_by(ili.id.asc())
        )
        out: list[dict[str, Any]] = []
        for li, pname, pcode in self._db.execute(stmt).all():
            q0 = int(li.quantity or 0)
            lid = li.id
            already = int(credited.get(lid, 0) or 0)
            rem = max(0, q0 - already)
            ht_full = invoice_line_ht_total(li)
            ttc_full = invoice_line_rounded_ttc(li)
            out.append(
                {
                    "invoice_line_id": str(li.id),
                    "product_id": str(li.product_id),
                    "product_name": str(pname or ""),
                    "product_code": (str(pcode).strip() if pcode else ""),
                    "quantity": q0,
                    "quantity_already_credited": already,
                    "quantity_remaining": rem,
                    "line_ht": round(ht_full, 4),
                    "line_ttc": round(ttc_full, 2),
                    "vat_percent": float(li.vat_rate),
                    "is_free_unit": bool(li.is_free_unit),
                }
            )
        return out

    def search_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "issueDate",
        order: str = "asc",
        status: str | None = None,
        invoice_number: str | None = None,
        pharmacy_id: str | None = None,
        pharmacy_name: str | None = None,
        overdue_only: bool = False,
        overdue_min_days: int = 0,
        deposit_id: str | None = None,
    ) -> PageResult[list[dict[str, Any]]]:
        p1, ps = normalize_page_input(page, page_size)
        off = offset_for_page(p1, ps)
        i, ph, dep = orm.Invoice, orm.Pharmacy, orm.Deposit
        cn = orm.CreditNote
        src_inv = aliased(orm.Invoice)
        today = date.today()
        st_raw = str(status).strip() if status else ""
        credit_only = st_raw == "avoir" and not overdue_only
        invoice_exclusive = overdue_only or (bool(st_raw) and st_raw != "avoir")
        null_str = cast(literal(None), String)
        null_src = cast(literal(None), PG_UUID(as_uuid=True))

        pid_filter: uuid.UUID | None = None
        if pharmacy_id and str(pharmacy_id).strip():
            try:
                pid_filter = mp.parse_uuid(str(pharmacy_id).strip())
            except ValueError:
                pid_filter = None

        def _deposit_uuid_or_none(raw: str) -> uuid.UUID | None:
            try:
                return mp.parse_uuid(raw)
            except ValueError:
                return None

        # --- Sélecteurs UNION (mêmes colonnes / labels) ---
        inv_union_sel = (
            select(
                literal("invoice").label("row_kind"),
                i.id.label("id"),
                i.pharmacy_id.label("pharmacy_id"),
                i.invoice_number.label("doc_number"),
                ph.name.label("pharmacy_name"),
                dep.bl_number.label("bl_number"),
                i.amount.label("amount"),
                i.issue_date.label("issue_date"),
                i.due_date.label("due_date"),
                i.status.label("status"),
                i.days_overdue.label("days_overdue"),
                i.external_provider.label("external_provider"),
                i.external_invoice_id.label("external_invoice_id"),
                null_str.label("external_credit_note_id"),
                i.deposit_id.label("deposit_id"),
                null_src.label("source_invoice_id"),
                i.payment_date.label("payment_date"),
            )
            .select_from(i)
            .join(ph, i.pharmacy_id == ph.id)
            .outerjoin(dep, i.deposit_id == dep.id)
        )
        cn_union_sel = (
            select(
                literal("credit_note").label("row_kind"),
                cn.id.label("id"),
                cn.pharmacy_id.label("pharmacy_id"),
                cn.credit_note_number.label("doc_number"),
                ph.name.label("pharmacy_name"),
                dep.bl_number.label("bl_number"),
                cn.amount_ttc.label("amount"),
                cn.issue_date.label("issue_date"),
                cn.issue_date.label("due_date"),
                literal("avoir").label("status"),
                cast(literal(0), Integer).label("days_overdue"),
                cn.external_provider.label("external_provider"),
                null_str.label("external_invoice_id"),
                cn.external_credit_note_id.label("external_credit_note_id"),
                src_inv.deposit_id.label("deposit_id"),
                cn.source_invoice_id.label("source_invoice_id"),
                cast(literal(None), Date).label("payment_date"),
            )
            .select_from(cn)
            .join(ph, cn.pharmacy_id == ph.id)
            .outerjoin(src_inv, cn.source_invoice_id == src_inv.id)
            .outerjoin(dep, src_inv.deposit_id == dep.id)
        )

        def conds_credit_note() -> list[Any]:
            c_conds: list[Any] = []
            if invoice_number and str(invoice_number).strip():
                qn = f"%{str(invoice_number).strip()}%"
                c_conds.append(
                    or_(
                        cn.credit_note_number.ilike(qn),
                        src_inv.invoice_number.ilike(qn),
                    )
                )
            if pid_filter is not None:
                c_conds.append(cn.pharmacy_id == pid_filter)
            if pharmacy_name and str(pharmacy_name).strip():
                qph = f"%{str(pharmacy_name).strip()}%"
                c_conds.append(ph.name.ilike(qph))
            if deposit_id and str(deposit_id).strip():
                raw_dep = str(deposit_id).strip()
                uuid_dep = _deposit_uuid_or_none(raw_dep)
                if uuid_dep is not None:
                    c_conds.append(src_inv.deposit_id == uuid_dep)
                else:
                    c_conds.append(dep.bl_number.ilike(f"%{raw_dep}%"))
            return c_conds

        def conds_invoice(status_val: str | None) -> list[Any]:
            c_conds: list[Any] = []
            if status_val:
                c_conds.append(i.status == status_val)
            if invoice_number and str(invoice_number).strip():
                qn = f"%{str(invoice_number).strip()}%"
                c_conds.append(i.invoice_number.ilike(qn))
            if pid_filter is not None:
                c_conds.append(i.pharmacy_id == pid_filter)
            if pharmacy_name and str(pharmacy_name).strip():
                qph = f"%{str(pharmacy_name).strip()}%"
                c_conds.append(ph.name.ilike(qph))
            if deposit_id and str(deposit_id).strip():
                raw_dep = str(deposit_id).strip()
                uuid_dep = _deposit_uuid_or_none(raw_dep)
                if uuid_dep is not None:
                    c_conds.append(i.deposit_id == uuid_dep)
                else:
                    c_conds.append(dep.bl_number.ilike(f"%{raw_dep}%"))
            if overdue_only:
                dmin = max(0, int(overdue_min_days))
                c_conds.append(~i.status.in_(("paid", "credited", "cancelled")))
                c_conds.append(i.due_date < today)
                c_conds.append((func.current_date() - i.due_date) >= dmin)
            return c_conds

        skey = sort if sort in INVOICE_SORT_KEYS else "issueDate"

        if credit_only:
            cn_conds = conds_credit_note()
            cq = cn_union_sel.where(and_(*cn_conds)) if cn_conds else cn_union_sel
            cq_sub = cq.subquery()
            total = int(self._db.execute(select(func.count()).select_from(cq_sub)).scalar() or 0)
            ob_u = _order_clause_union(skey, order, cq_sub)
            urows = self._db.execute(select(cq_sub).order_by(ob_u).offset(off).limit(ps)).all()
            items_cn = [_union_row_to_api_dict(row) for row in urows]
            return PageResult(items=items_cn, total=total, page=p1, page_size=ps)

        if invoice_exclusive:
            i_conds = conds_invoice(st_raw or None)
            where = and_(*i_conds) if i_conds else None
            base = (
                select(i, ph.name, dep.bl_number)
                .select_from(i)
                .join(ph, i.pharmacy_id == ph.id)
                .outerjoin(dep, i.deposit_id == dep.id)
            )
            if where is not None:
                base = base.where(where)
            count_q = (
                select(func.count()).select_from(i).join(ph, i.pharmacy_id == ph.id).outerjoin(dep, i.deposit_id == dep.id)
            )
            if where is not None:
                count_q = count_q.where(where)
            total = int(self._db.execute(count_q).scalar() or 0)
            ob = _order_clause(skey, order, i, ph, dep)
            raw_rows = self._db.execute(base.order_by(ob).offset(off).limit(ps)).all()
            inv_rows = [row[0] for row in raw_rows]
            has_cn_set = frozenset()
            if inv_rows:
                iuuids = [r.id for r in inv_rows]
                cn_existing = (
                    self._db.execute(
                        select(orm.CreditNote.source_invoice_id)
                        .where(orm.CreditNote.source_invoice_id.in_(iuuids))
                        .distinct()
                    )
                    .scalars()
                    .all()
                )
                has_cn_set = frozenset(cn_existing)
            items_inv: list[dict[str, Any]] = []
            for row in raw_rows:
                inv_row, pname, bln = row[0], row[1], row[2]
                has_cn = inv_row.id in has_cn_set
                items_inv.append(
                    _invoice_tuple_to_api_dict(
                        mp.invoice_orm_to_domain(inv_row),
                        str(pname) if pname is not None else None,
                        str(bln) if bln is not None else None,
                        bool(has_cn),
                    )
                )
            return PageResult(items=items_inv, total=total, page=p1, page_size=ps)

        # Union factures + avoirs (filtre « Tous » sur le statut)
        inv_conds_union = conds_invoice(None)
        cn_conds_u = conds_credit_note()
        inv_side = inv_union_sel.where(and_(*inv_conds_union)) if inv_conds_union else inv_union_sel
        cn_side = cn_union_sel.where(and_(*cn_conds_u)) if cn_conds_u else cn_union_sel
        u_sub = union_all(inv_side, cn_side).subquery()
        total = int(self._db.execute(select(func.count()).select_from(u_sub)).scalar() or 0)
        ob_union = _order_clause_union(skey, order, u_sub)
        urows_raw = self._db.execute(select(u_sub).order_by(ob_union).offset(off).limit(ps)).all()

        invoice_ids_have_cn = [row.id for row in urows_raw if row.row_kind == "invoice"]
        has_cn_union: frozenset = frozenset()
        if invoice_ids_have_cn:
            cn_existing = (
                self._db.execute(
                    select(orm.CreditNote.source_invoice_id)
                    .where(orm.CreditNote.source_invoice_id.in_(invoice_ids_have_cn))
                    .distinct()
                )
                .scalars()
                .all()
            )
            has_cn_union = frozenset(cn_existing)

        merged: list[dict[str, Any]] = []
        for row in urows_raw:
            d = _union_row_to_api_dict(row)
            if row.row_kind == "invoice":
                d["has_credit_notes"] = row.id in has_cn_union
            merged.append(d)
        return PageResult(items=merged, total=total, page=p1, page_size=ps)

    def find_by_id(self, id_: str) -> Optional[Invoice]:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Invoice, iid)
        return mp.invoice_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[Invoice]:
        q = select(orm.Invoice)
        for k, v in kwargs.items():
            if k == "pharmacy_id" and v is not None:
                v = mp.parse_uuid(v)
            if k == "sage_reference":
                k = "reference_external"
            if not hasattr(orm.Invoice, k):
                continue
            q = q.where(getattr(orm.Invoice, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.invoice_orm_to_domain(r) for r in rows]

    def find_by_pharmacy(self, pharmacy_id: str) -> list[Invoice]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def pharmacy_invoice_detail_dicts(self, pharmacy_id: str) -> list[dict[str, Any]]:
        """Factures d'une pharmacie avec totaux ligne (bouteilles payantes, remise) et n° BL lié."""
        try:
            pid = mp.parse_uuid(pharmacy_id)
        except ValueError:
            return []

        ordered = (
            self._db.execute(
                select(orm.Invoice, orm.Deposit.bl_number)
                .outerjoin(orm.Deposit, orm.Invoice.deposit_id == orm.Deposit.id)
                .where(orm.Invoice.pharmacy_id == pid)
                .order_by(orm.Invoice.issue_date.desc())
            )
            .all()
        )
        if not ordered:
            return []

        iuuids = [inv.id for inv, _ in ordered]
        line_rows = (
            self._db.execute(select(orm.InvoiceLine).where(orm.InvoiceLine.invoice_id.in_(iuuids)))
            .scalars()
            .all()
        )

        invoices_with_cn = frozenset(
            self._db.execute(
                select(orm.CreditNote.source_invoice_id)
                .where(orm.CreditNote.source_invoice_id.in_(iuuids))
                .distinct()
            )
            .scalars()
            .all()
        )

        agg: dict[Any, dict[str, Any]] = {}
        for li in line_rows:
            iid = li.invoice_id
            if iid not in agg:
                agg[iid] = {"paying_bottles": 0, "discount": 0.0}
            if not li.is_free_unit:
                agg[iid]["paying_bottles"] += int(li.quantity)
                d = float(li.discount_percent or 0)
                if int(li.quantity) > 0 and d > agg[iid]["discount"]:
                    agg[iid]["discount"] = d

        out: list[dict[str, Any]] = []
        for inv_row, bln in ordered:
            inv = mp.invoice_orm_to_domain(inv_row)
            a = agg.get(inv_row.id, {"paying_bottles": 0, "discount": 0.0})
            d = inv.to_dict()
            d["paying_bottles"] = int(a["paying_bottles"])
            disc = float(a["discount"] or 0)
            d["line_discount_percent"] = round(disc, 2) if disc > 0 else None
            d["deposit_bl_number"] = (str(bln).strip() if bln else None)
            d["has_credit_notes"] = inv_row.id in invoices_with_cn
            out.append(d)
        return out

    def find_overdue(self, days: int = 30) -> list[Invoice]:
        return [
            inv
            for inv in self.find_all()
            if inv.status == "overdue" and inv.days_overdue >= days
        ]

    def create(self, model: Invoice, lines: list[dict] | None = None) -> Invoice:
        pd = mp.parse_date(model.payment_date) if model.payment_date else None
        sale_d = mp.parse_date(model.sale_date) if model.sale_date else None
        dep_id = mp.parse_uuid(model.deposit_id) if model.deposit_id else None
        vr_id = mp.parse_uuid(model.visit_report_id) if model.visit_report_id else None
        row = orm.Invoice(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            deposit_id=dep_id,
            visit_report_id=vr_id,
            invoice_number=model.invoice_number,
            amount=float(model.amount),
            issue_date=mp.parse_date(model.issue_date),
            due_date=mp.parse_date(model.due_date),
            sale_date=sale_d,
            invoice_billing_type=model.billing_type,
            amount_ht=float(model.amount_ht) if model.amount_ht is not None else None,
            amount_vat=float(model.amount_vat) if model.amount_vat is not None else None,
            amount_ttc=float(model.amount_ttc) if model.amount_ttc is not None else None,
            status=model.status,
            payment_date=pd,
            reference_external=model.sage_reference,
            external_provider=model.external_provider,
            external_invoice_id=model.external_invoice_id,
            mock_provider_payload=model.mock_provider_payload,
            days_overdue=int(model.days_overdue or 0),
        )
        self._db.add(row)
        self._db.flush()
        if lines:
            for li in lines:
                self._db.add(
                    orm.InvoiceLine(
                        invoice_id=row.id,
                        product_id=mp.parse_uuid(li["product_id"]),
                        quantity=int(li["quantity"]),
                        unit_price=float(li["unit_price"]),
                        vat_rate=float(li["vat_rate"]),
                        is_free_unit=bool(li.get("is_free_unit", False)),
                        discount_percent=float(li.get("discount_percent", 0) or 0),
                        line_total_ht=(
                            float(li["line_total_ht"]) if li.get("line_total_ht") is not None else None
                        ),
                        reference_unit_price_ht=(
                            float(li["reference_unit_price_ht"])
                            if li.get("reference_unit_price_ht") is not None
                            else None
                        ),
                    )
                )
            self._db.flush()
        return mp.invoice_orm_to_domain(row)

    def invoice_summaries_by_deposit_ids(
        self, deposit_ids: list[str]
    ) -> dict[str, list[dict[str, str]]]:
        """Pour chaque id de dépôt, liste {id, invoice_number} des factures liées (issue_date desc)."""
        if not deposit_ids:
            return {}
        uuids = []
        for d in deposit_ids:
            try:
                uuids.append(mp.parse_uuid(str(d).strip()))
            except ValueError:
                continue
        if not uuids:
            return {}
        rows = self._db.execute(
            select(orm.Invoice.deposit_id, orm.Invoice.id, orm.Invoice.invoice_number)
            .where(orm.Invoice.deposit_id.in_(uuids))
            .order_by(orm.Invoice.issue_date.desc())
        ).all()
        out: dict[str, list[dict[str, str]]] = defaultdict(list)
        for dep_id, iid, num in rows:
            if dep_id is None:
                continue
            out[str(dep_id)].append(
                {"id": str(iid), "invoice_number": str(num) if num is not None else ""}
            )
        return dict(out)

    def update(self, id_: str, model: Invoice) -> Optional[Invoice]:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Invoice, iid)
        if not row:
            return None
        row.pharmacy_id = mp.parse_uuid(model.pharmacy_id)
        row.deposit_id = mp.parse_uuid(model.deposit_id) if model.deposit_id else None
        row.visit_report_id = mp.parse_uuid(model.visit_report_id) if model.visit_report_id else None
        row.invoice_number = model.invoice_number
        row.amount = float(model.amount)
        row.issue_date = mp.parse_date(model.issue_date)
        row.due_date = mp.parse_date(model.due_date)
        row.sale_date = mp.parse_date(model.sale_date) if model.sale_date else None
        row.invoice_billing_type = model.billing_type
        row.amount_ht = float(model.amount_ht) if model.amount_ht is not None else None
        row.amount_vat = float(model.amount_vat) if model.amount_vat is not None else None
        row.amount_ttc = float(model.amount_ttc) if model.amount_ttc is not None else None
        row.status = model.status
        row.payment_date = mp.parse_date(model.payment_date) if model.payment_date else None
        row.reference_external = model.sage_reference
        row.external_provider = model.external_provider
        row.external_invoice_id = model.external_invoice_id
        row.mock_provider_payload = model.mock_provider_payload
        row.days_overdue = int(model.days_overdue or 0)
        self._db.flush()
        return mp.invoice_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            iid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Invoice, iid)
        if not row:
            return False
        self._db.delete(row)
        return True
