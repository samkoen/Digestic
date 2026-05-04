"""Client HTTP API VosFactures (POST invoices.json)."""

from __future__ import annotations

import json
import urllib.parse
from datetime import date
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.integrations.vosfactures.config import (
    vosfactures_api_token,
    vosfactures_department_id,
    vosfactures_seller_name,
    vosfactures_subdomain,
    vosfactures_test_documents,
)
from app.integrations.vosfactures.types import (
    VosFacturesCreditNoteResult,
    VosFacturesInvoiceResult,
)
from app.models.pharmacy import Pharmacy

PROVIDER_KEY = "vosfactures"


def _parse_invoice_from_create_response(raw: Any) -> dict[str, Any] | None:
    """La JSON API renvoie soit `{"invoice": {...}}`, soit la facture directement à la racine."""
    if not isinstance(raw, dict):
        return None
    inv = raw.get("invoice")
    if isinstance(inv, dict):
        return inv
    if raw.get("id") is not None and (
        raw.get("number") is not None
        or raw.get("kind") in ("vat", "receipt", "proforma", "correction")
        or raw.get("status") is not None
    ):
        return raw
    return None


def _parse_vf_decimal(val: Any) -> float | None:
    """Interprète un montant renvoyé par VosFactures (nombre ou chaîne avec virgule)."""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def totals_abs_from_vf_document(inv: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    """(HT, TVA, TTC) en valeurs positives si les champs existent."""
    ttc_raw = (
        _parse_vf_decimal(inv.get("total_price_gross"))
        or _parse_vf_decimal(inv.get("price_gross"))
    )
    ht = _parse_vf_decimal(inv.get("total_price_net"))
    ttc = abs(ttc_raw) if ttc_raw is not None else None
    if ht is not None:
        ht = abs(ht)
    vat = None
    if ttc is not None and ht is not None:
        vat = abs(ttc - ht)
    return ht, vat, ttc


class VosFacturesApiClient:
    def __init__(
        self,
        *,
        subdomain: str | None = None,
        api_token: str | None = None,
    ):
        self._sub = (subdomain or vosfactures_subdomain() or "").strip().lower()
        self._token = api_token or vosfactures_api_token() or ""
        if not self._sub or not self._token:
            raise ValueError("VosFactures : sous-domaine et jeton API requis")

    def _url_invoices(self) -> str:
        return f"https://{self._sub}.vosfactures.fr/invoices.json"

    @staticmethod
    def _fmt_discount_percent_for_vf(pct: float) -> str:
        """Chaîne attendue par VosFactures pour discount_percent (%)."""
        p = float(pct)
        if abs(p - round(p)) < 1e-9:
            return str(int(round(p)))
        return f"{p:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def _build_positions(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        positions: list[dict[str, Any]] = []
        for li in lines:
            nature = li.get("nature", "paying")
            qty = int(li.get("quantity", 0))
            if qty <= 0:
                continue
            tax = float(li.get("vat_rate_percent", 0))
            label = str(li.get("label", "Produit"))
            code = (li.get("product_code") or "").strip()
            code_field = {"code": code} if code else {}

            if nature == "paying":
                line_ht = float(li.get("line_ht", 0))
                unit_ht_catalog = float(li.get("unit_price_ht") or 0)
                d_pct = float(li.get("discount_percent") or 0)
                use_breakdown = d_pct > 0 and unit_ht_catalog > 0
                if use_breakdown:
                    # Doc VosFactures : prix avant réduction obligatoires ; total_price_gross requis même avec price_net.
                    gross_ht = round(qty * unit_ht_catalog, 4)
                    gross_ttc = round(gross_ht * (1 + tax / 100.0), 2)
                    positions.append(
                        {
                            "name": label,
                            **code_field,
                            "quantity": qty,
                            "tax": tax,
                            "price_net": unit_ht_catalog,
                            "total_price_gross": gross_ttc,
                            "discount_percent": VosFacturesApiClient._fmt_discount_percent_for_vf(
                                d_pct
                            ),
                        }
                    )
                else:
                    ttc = round(line_ht * (1 + tax / 100.0), 2)
                    positions.append(
                        {
                            "name": label,
                            **code_field,
                            "quantity": qty,
                            "tax": tax,
                            "total_price_gross": ttc,
                        }
                    )
            else:
                ref_ht = float(li.get("reference_value_ht") or li.get("unit_price_ht") or 0)
                desc = (
                    f"Unité gratuite — valeur de référence HT unitaire {ref_ht:.4f} €"
                    if ref_ht
                    else "Unité gratuite (UG)"
                )
                positions.append(
                    {
                        "name": label,
                        **code_field,
                        "description": desc,
                        "quantity": qty,
                        "tax": tax,
                        "total_price_gross": 0.0,
                    }
                )
        return positions

    def _build_buyer(self, pharmacy: Pharmacy | None) -> dict[str, Any]:
        if not pharmacy:
            return {
                "buyer_name": "Client",
                "buyer_company": True,
            }
        buyer: dict[str, Any] = {
            "buyer_name": pharmacy.name.strip(),
            "buyer_company": True,
        }
        if pharmacy.address:
            buyer["buyer_street"] = str(pharmacy.address).strip()
        if pharmacy.postal_code:
            buyer["buyer_post_code"] = str(pharmacy.postal_code).strip()
        if pharmacy.city:
            buyer["buyer_city"] = str(pharmacy.city).strip()
        if pharmacy.country:
            buyer["buyer_country"] = str(pharmacy.country).strip().upper()[:2]
        if pharmacy.email:
            buyer["buyer_email"] = str(pharmacy.email).strip()
        phone = pharmacy.phone or pharmacy.pharmacist_phone
        if phone:
            buyer["buyer_phone"] = str(phone).strip()
        return buyer

    def issue_vat_invoice(
        self,
        *,
        draft_invoice_number: str,
        pharmacy: Pharmacy | None,
        issue_date: date,
        sale_date: date,
        due_date: date,
        lines: list[dict[str, Any]],
        totals: dict[str, float],
        billing_type: str,
        internal_deposit_id: str | None,
        invoice_public_reference: str | None = None,
        currency: str = "EUR",
        digestic_bl_number: str | None = None,
    ) -> VosFacturesInvoiceResult:
        positions = self._build_positions(lines)
        if not positions:
            raise ValueError("VosFactures : aucune ligne de facture à envoyer")

        invoice_level_discount = any(
            str(li.get("nature") or "paying") == "paying"
            and float(li.get("discount_percent") or 0) > 0
            and float(li.get("unit_price_ht") or 0) > 0
            for li in lines
        )

        inv: dict[str, Any] = {
            "kind": "vat",
            "lang": "fr",
            "currency": (currency or "EUR")[:3].upper(),
            "seller_name": vosfactures_seller_name(),
            "issue_date": issue_date.isoformat(),
            "sell_date": sale_date.isoformat(),
            "payment_to_kind": "other_date",
            "payment_to": due_date.isoformat(),
            "positions": positions,
            "oid": draft_invoice_number,
            "oid_unique": "yes",
        }
        # Doc VosFactures : remise × ligne (discount_percent) + prix avant remise → affichage comme le BL (HT).
        if invoice_level_discount:
            inv["show_discount"] = True
            inv["discount_kind"] = "percent_unit"
        dept = vosfactures_department_id()
        if dept is not None:
            inv["department_id"] = dept

        inv.update(self._build_buyer(pharmacy))

        if vosfactures_test_documents():
            inv["test"] = True

        desc_lines: list[str] = []
        bln = (digestic_bl_number or "").strip()
        if bln:
            desc_lines.append(f"N° bon de livraison : {bln}")
        ref = (invoice_public_reference or "").strip()
        if ref:
            desc_lines.append(f"Réf. Sage / externe : {ref}")
        if desc_lines:
            inv["description"] = "\n".join(desc_lines)

        body = {"api_token": self._token, "invoice": inv}

        raw = self._post_json(self._url_invoices(), body)
        if isinstance(raw, dict) and raw.get("code") == "error":
            raise ValueError(f"VosFactures : {raw.get('message', raw)}")

        invoice = _parse_invoice_from_create_response(raw)
        if not isinstance(invoice, dict):
            raise ValueError(f"VosFactures : réponse inattendue {raw!r}")

        ext_id = invoice.get("id")
        num = invoice.get("number")

        enriched = {
            "vosfactures_response": raw,
            "digestic_meta": {
                "billing_type": billing_type,
                "totals": totals,
                "lines": lines,
                "internal_deposit_id": internal_deposit_id,
                "invoice_public_reference": ref or None,
                "digestic_bl_number": bln or None,
            },
        }

        return VosFacturesInvoiceResult(
            provider=PROVIDER_KEY,
            external_id=str(ext_id) if ext_id is not None else None,
            invoice_number=str(num) if num else None,
            payload=enriched,
        )

    def issue_total_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
    ) -> VosFacturesCreditNoteResult:
        """Avoir total lié à une facture VosFactures (doc. API : copy_invoice_from + kind correction)."""
        vid = str(from_external_invoice_id).strip()
        if not vid:
            raise ValueError("Identifiant facture VosFactures (source) manquant")
        reason = (correction_reason or "").strip() or "Avoir"
        inv: dict[str, Any] = {
            "kind": "correction",
            "total_correction": "1",
            "correction_reason": reason,
            "lang": "fr",
        }
        if vid.isdigit():
            inv["copy_invoice_from"] = int(vid)
        else:
            inv["copy_invoice_from"] = vid
        dept = vosfactures_department_id()
        if dept is not None:
            inv["department_id"] = dept
        if vosfactures_test_documents():
            inv["test"] = True
        body = {"api_token": self._token, "invoice": inv}
        raw = self._post_json(self._url_invoices(), body)
        if isinstance(raw, dict) and raw.get("code") == "error":
            raise ValueError(f"VosFactures : {raw.get('message', raw)}")
        parsed = _parse_invoice_from_create_response(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"VosFactures : réponse inattendue {raw!r}")
        ext_id = parsed.get("id")
        num = parsed.get("number")
        enriched = {
            "vosfactures_response": raw,
            "digestic_meta": {"correction_kind": "total", "from_external_invoice_id": vid},
        }
        return VosFacturesCreditNoteResult(
            provider=PROVIDER_KEY,
            external_id=str(ext_id) if ext_id is not None else None,
            credit_note_number=str(num) if num else None,
            payload=enriched,
        )

    def issue_partial_credit_note(
        self,
        *,
        from_external_invoice_id: str,
        correction_reason: str,
        positions: list[dict[str, Any]],
        lang: str = "fr",
    ) -> VosFacturesCreditNoteResult:
        """Avoir partiel (sans total_correction). Voir doc. API correction + positions avant/après."""
        vid = str(from_external_invoice_id).strip()
        if not vid:
            raise ValueError("Identifiant facture VosFactures (source) manquant")
        if not positions:
            raise ValueError("Au moins une ligne de correction est requise.")
        reason = (correction_reason or "").strip() or "Avoir partiel"

        vf_id_txt = vid
        inv: dict[str, Any] = {
            "kind": "correction",
            "correction_reason": reason,
            "invoice_id": vf_id_txt,
            "from_invoice_id": vf_id_txt,
            "positions": positions,
            "lang": (lang or "fr")[:4],
        }

        dept = vosfactures_department_id()
        if dept is not None:
            inv["department_id"] = dept
        if vosfactures_test_documents():
            inv["test"] = True

        body = {"api_token": self._token, "invoice": inv}
        raw = self._post_json(self._url_invoices(), body)
        if isinstance(raw, dict) and raw.get("code") == "error":
            raise ValueError(f"VosFactures : {raw.get('message', raw)}")
        parsed = _parse_invoice_from_create_response(raw)
        if not isinstance(parsed, dict):
            raise ValueError(f"VosFactures : réponse inattendue {raw!r}")
        ext_id = parsed.get("id")
        num = parsed.get("number")
        enriched = {
            "vosfactures_response": raw,
            "digestic_meta": {
                "correction_kind": "partial",
                "from_external_invoice_id": vf_id_txt,
                "positions_preview": positions,
            },
        }
        return VosFacturesCreditNoteResult(
            provider=PROVIDER_KEY,
            external_id=str(ext_id) if ext_id is not None else None,
            credit_note_number=str(num) if num else None,
            payload=enriched,
        )

    def register_invoice_payment(
        self,
        *,
        vosfactures_invoice_id: str,
        paid_date_iso: str,
        price_ttc: float,
        payment_name: str = "Encaissement Digestic",
    ) -> dict[str, Any]:
        """Enregistre un paiement lié à la facture VF (voir doc : POST banking/payments.json)."""
        vid = str(vosfactures_invoice_id).strip()
        if not vid:
            raise ValueError("Identifiant facture VosFactures manquant")
        date_chunk = str(paid_date_iso or "").strip()[:10]
        if len(date_chunk) != 10 or date_chunk[4] != "-" or date_chunk[7] != "-":
            raise ValueError("paid_date doit être au format YYYY-MM-DD.")

        amt = round(float(price_ttc), 2)
        if amt <= 0:
            raise ValueError("Montant TTC doit être positif pour enregistrer le paiement VosFactures.")

        invoice_id_field: Any = int(vid) if vid.isdigit() else vid

        banking_payment: dict[str, Any] = {
            "name": payment_name.strip() or "Encaissement Digestic",
            "price": amt,
            "invoice_id": invoice_id_field,
            "paid": True,
            "kind": "api",
            "paid_date": date_chunk,
            "currency": "EUR",
        }
        dept = vosfactures_department_id()
        if dept is not None:
            banking_payment["department_id"] = dept

        body = {"api_token": self._token, "banking_payment": banking_payment}
        url = f"https://{self._sub}.vosfactures.fr/banking/payments.json"
        raw = self._post_json(url, body)
        if isinstance(raw, dict) and raw.get("code") == "error":
            raise ValueError(f"VosFactures : {raw.get('message', raw)}")
        return raw if isinstance(raw, dict) else {"response": raw}

    def fetch_invoice_pdf(self, vosfactures_invoice_id: str) -> bytes:
        """GET /invoices/{id}.pdf — doc. officielle API VosFactures."""
        vid = str(vosfactures_invoice_id).strip()
        if not vid:
            raise ValueError("Identifiant facture VosFactures manquant")
        q = urllib.parse.urlencode({"api_token": self._token})
        url = f"https://{self._sub}.vosfactures.fr/invoices/{vid}.pdf?{q}"
        req = Request(
            url,
            method="GET",
            headers={"Accept": "application/pdf,*/*"},
        )
        try:
            with urlopen(req, timeout=90) as resp:
                return resp.read()
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:800]
            raise ValueError(
                f"VosFactures PDF HTTP {e.code}: {err_body or e.reason}"
            ) from e

    def _post_json(self, url: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = Request(
            url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=90) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return json.loads(text) if text.strip() else {}
        except HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body) if err_body.strip() else {}
            except json.JSONDecodeError:
                parsed = {"raw": err_body}
            raise ValueError(f"VosFactures HTTP {e.code}: {parsed}") from e
