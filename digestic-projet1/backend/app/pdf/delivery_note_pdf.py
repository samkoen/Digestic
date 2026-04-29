"""PDF bon de livraison — mise en forme proche des documents Sage / Digestic (facture & BL)."""
from __future__ import annotations

import io
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.repositories.product_repository import get_default_billing_product_row

# Identité émetteur (aligné factures / BL papier Digestic)
_ISSUER_NAME = "DIGESTIC"
_ISSUER_LINES = [
    "www.digestic-health.com",
    "comptabilite@digestic.fr",
    "01.86.98.34.93",
]
_FOOTER_LEGAL = (
    "En cas de retard de paiement, une pénalité calculée sur la base de trois fois "
    "l'intérêt légal en vigueur ainsi qu'une indemnité forfaitaire pour frais de recouvrement "
    "de 40 euros seront exigibles (art. L.441-6 et D.441-5 du code de commerce)."
)
_FOOTER_COMPANY = [
    "LES LABORATOIRES DIGESTIC",
    "IBAN FR76 1695 8000 0193 4517 0749 225 — BIC QNTOFRP1XXX",
    "N° Siret 80889182400027 — N° TVA intracommunautaire FR03808891824",
    "Tél. 01.86.98.34.93 — comptabilite@digestic.fr — www.digestic-health.com",
]


def _fr_amount(x: float | Decimal, decimals: int = 2) -> str:
    v = float(x)
    s = f"{v:.{decimals}f}"
    return s.replace(".", ",")


def _vat_code(rate: float) -> str:
    if abs(rate - 5.5) < 0.05:
        return "C55"
    if abs(rate - 20.0) < 0.01:
        return "C20"
    if rate == int(rate):
        return f"C{int(rate)}"
    return f"C{rate:.1f}".replace(".", "")


@dataclass
class _PdfLine:
    ref: str
    label: str
    qty: float
    unit_ht: float
    discount_pct: float
    line_ht: float
    vat_rate: float


def _paragraph_styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        name="BLTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=colors.HexColor("#1a5f5f"),
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        name="BLSub",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
    )
    small = ParagraphStyle(
        name="BLSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#333333"),
    )
    right = ParagraphStyle(
        name="BLRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT,
    )
    center_brand = ParagraphStyle(
        name="BLCenterBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a5f5f"),
    )
    footer = ParagraphStyle(
        name="BLFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6,
        leading=8,
        textColor=colors.HexColor("#555555"),
    )
    return styles, title, subtitle, small, right, center_brand, footer


def _build_lines_for_deposit(db: Session, dep: orm.Deposit) -> list[_PdfLine]:
    rows = db.execute(
        select(orm.DepositLine, orm.Product)
        .join(orm.Product, orm.DepositLine.product_id == orm.Product.id)
        .where(orm.DepositLine.deposit_id == dep.id)
        .order_by(orm.Product.name)
    ).all()

    out: list[_PdfLine] = []
    for dl, pr in rows:
        qty = int(dl.quantity)
        unit = float(pr.wholesale_unit_price)
        vat = float(pr.vat_rate)
        lht = round(qty * unit, 2)
        code = (pr.code or "").strip() or "—"
        out.append(
            _PdfLine(
                ref=code,
                label=pr.name or "—",
                qty=float(qty),
                unit_ht=unit,
                discount_pct=0.0,
                line_ht=lht,
                vat_rate=vat,
            )
        )

    fq = int(dep.free_units_quantity or 0)
    if fq > 0:
        pr = None
        if rows:
            pr = rows[0][1]
        if pr is None:
            pr = get_default_billing_product_row(db)
        if pr:
            vat = float(pr.vat_rate)
            code = (pr.code or "").strip() or "—"
            out.append(
                _PdfLine(
                    ref=code,
                    label=f"{pr.name} (UG)",
                    qty=float(fq),
                    unit_ht=0.0,
                    discount_pct=100.0,
                    line_ht=0.0,
                    vat_rate=vat,
                )
            )

    if not out and int(dep.bottles_count or 0) > 0:
        pr = get_default_billing_product_row(db)
        if pr:
            qty = int(dep.bottles_count)
            unit = float(pr.wholesale_unit_price)
            vat = float(pr.vat_rate)
            lht = round(qty * unit, 2)
            code = (pr.code or "").strip() or "—"
            out.append(
                _PdfLine(
                    ref=code,
                    label=pr.name or "—",
                    qty=float(qty),
                    unit_ht=unit,
                    discount_pct=0.0,
                    line_ht=lht,
                    vat_rate=vat,
                )
            )
    return out


def build_delivery_note_pdf(db: Session, note_id: str) -> tuple[bytes, str] | None:
    """Construit le PDF d'un bon (dépôt). Retourne (octets, nom de fichier) ou None si introuvable."""
    try:
        did = mp.parse_uuid(str(note_id).strip())
    except ValueError:
        return None

    dep = db.get(orm.Deposit, did)
    if not dep:
        return None

    ph = db.get(orm.Pharmacy, dep.pharmacy_id)
    if not ph:
        return None

    lines = _build_lines_for_deposit(db, dep)

    dd: date = dep.delivery_date
    date_str = dd.strftime("%d/%m/%y")
    bl = (dep.bl_number or "").strip() or str(did)
    doc_title_num = bl
    if not bl.startswith("BL"):
        doc_title_num = bl

    vat_bases: dict[float, float] = defaultdict(float)
    for ln in lines:
        vat_bases[ln.vat_rate] += ln.line_ht

    total_ht = round(sum(vat_bases.values()), 2)
    total_vat = round(
        sum(round(base * (rate / 100.0), 2) for rate, base in vat_bases.items()),
        2,
    )
    total_ttc = round(total_ht + total_vat, 2)

    pay_mode = (ph.payment_mode or "").strip() or "selon conditions convenues"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=f"Bon de livraison {bl}",
    )

    _, title_st, subtitle_st, small_st, right_st, center_brand, footer_st = _paragraph_styles()

    client_lines = [
        escape(ph.name or ""),
        escape(f"{ph.address_line or ''}".strip()),
        escape(f"{ph.postal_code or ''} {ph.city or ''}".strip()),
    ]
    client_block = "<br/>".join(x for x in client_lines if x)

    hdr_inner = Table(
        [
            [
                Paragraph("<br/>".join(_ISSUER_LINES), small_st),
                Paragraph(client_block, right_st),
            ]
        ],
        colWidths=[doc.width / 2.0, doc.width / 2.0],
    )
    hdr_inner.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story: list[Any] = [
        Paragraph(escape(_ISSUER_NAME), center_brand),
        Spacer(1, 4 * mm),
        hdr_inner,
        Spacer(1, 5 * mm),
        Paragraph("DEPOT VENTE", subtitle_st),
        Spacer(1, 2 * mm),
        Paragraph(
            escape(f"Bon de livraison N° {doc_title_num}"),
            title_st,
        ),
        Paragraph(escape(f"le {date_str}"), small_st),
        Spacer(1, 3 * mm),
        Paragraph(escape("N° intracommunautaire"), small_st),
        Spacer(1, 4 * mm),
    ]

    livraison_r = escape(f"Livraison Num : {bl}     Du : {date_str}")
    liv_box = Table([[Paragraph(livraison_r, small_st)]], colWidths=[doc.width])
    liv_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#888888")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(liv_box)
    story.append(Spacer(1, 3 * mm))

    item_header = [
        "Référence",
        "Désignation",
        "Qté",
        "Px unitaire",
        "Remise",
        "Montant HT",
        "",
    ]
    item_rows: list[list[Any]] = [item_header]
    for ln in lines:
        rem = f"{_fr_amount(ln.discount_pct, 0)} %" if ln.discount_pct else ""
        item_rows.append(
            [
                escape(ln.ref[:24]),
                Paragraph(escape(ln.label[:200]), small_st),
                _fr_amount(ln.qty, 2),
                _fr_amount(ln.unit_ht, 2),
                rem,
                _fr_amount(ln.line_ht, 2),
                _vat_code(ln.vat_rate),
            ]
        )

    if len(item_rows) == 1:
        item_rows.append(
            [
                "—",
                Paragraph('<i>Aucune ligne de produit enregistrée</i>', small_st),
                "—",
                "—",
                "",
                "—",
                "",
            ]
        )

    cw = doc.width
    item_table = Table(
        item_rows,
        colWidths=[
            cw * 0.12,
            cw * 0.30,
            cw * 0.09,
            cw * 0.13,
            cw * 0.08,
            cw * 0.13,
            cw * 0.08,
        ],
        repeatRows=1,
    )
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bfbfbf")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("ALIGN", (4, 1), (5, -1), "RIGHT"),
                ("ALIGN", (6, 1), (6, -1), "CENTER"),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 6 * mm))

    tax_header = ["Code", "Base", "Taux", "Montant", "Total base", "Total montant taxe"]
    tax_data = [tax_header]
    run_base = 0.0
    run_tax = 0.0
    for rate in sorted(vat_bases.keys()):
        base = round(vat_bases[rate], 2)
        tax = round(base * (rate / 100.0), 2)
        run_base += base
        run_tax += tax
        tax_data.append(
            [
                _vat_code(rate),
                _fr_amount(base, 2),
                f"{_fr_amount(rate, 1)} %",
                _fr_amount(tax, 2),
                _fr_amount(run_base, 2),
                _fr_amount(run_tax, 2),
            ]
        )

    if len(tax_data) == 1:
        tax_data.append(["—", "—", "—", "—", _fr_amount(total_ht, 2), _fr_amount(total_vat, 2)])

    # Largeurs TVA sur toute la page (évite le chevauchement avec les totaux dans un tableau 2 col trop étroit).
    _tax_fracs = [0.12, 0.12, 0.10, 0.12, 0.14, 0.14]
    _tax_fracs_sum = sum(_tax_fracs)
    tax_col_widths = [cw * f / _tax_fracs_sum for f in _tax_fracs]
    tax_tbl = Table(tax_data, colWidths=tax_col_widths)
    tax_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#bfbfbf")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#999999")),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tax_tbl)
    story.append(Spacer(1, 5 * mm))

    tot_w = min(cw * 0.42, 72 * mm)
    tot_lines = [
        [Paragraph("<b>TOTAL HT</b>", small_st), Paragraph(f"<b>{_fr_amount(total_ht, 2)} €</b>", right_st)],
        [Paragraph("<b>TOTAL TVA</b>", small_st), Paragraph(f"<b>{_fr_amount(total_vat, 2)} €</b>", right_st)],
        [Paragraph("<b>TOTAL TTC</b>", small_st), Paragraph(f"<b>{_fr_amount(total_ttc, 2)} €</b>", right_st)],
    ]
    tot_tbl = Table(
        tot_lines,
        colWidths=[tot_w * 0.58, tot_w * 0.42],
        hAlign="RIGHT",
    )
    tot_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, colors.black),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(tot_tbl)
    story.append(Spacer(1, 5 * mm))

    cond = escape(
        f"Conditions de règlement : montant TTC {_fr_amount(total_ttc, 2)} € — {pay_mode} "
        f"(échéance facture à définir à l'émission de la facture)."
    )
    story.append(Paragraph(cond, small_st))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(escape(_FOOTER_LEGAL), footer_st))
    story.append(Spacer(1, 4 * mm))
    for fl in _FOOTER_COMPANY:
        story.append(Paragraph(escape(fl), footer_st))

    doc.build(story)
    raw = buffer.getvalue()

    safe_bl = re.sub(r"[^\w\-.]+", "_", bl, flags=re.UNICODE)[:72].strip("_") or "bon"
    filename = f"Bon_livraison_{safe_bl}.pdf"
    return raw, filename


def pdf_content_disposition_header(filename: str) -> str:
    """En-tête Content-Disposition avec encodage UTF-8 (RFC 5987)."""
    ascii_name = re.sub(r'[^A-Za-z0-9_.-]+', "_", filename)[:120]
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'
