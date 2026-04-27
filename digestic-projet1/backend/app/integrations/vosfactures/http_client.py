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
from app.integrations.vosfactures.types import VosFacturesInvoiceResult
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
        or raw.get("kind") in ("vat", "receipt", "proforma")
        or raw.get("status") is not None
    ):
        return raw
    return None


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
    def _build_positions(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
        positions: list[dict[str, Any]] = []
        for li in lines:
            nature = li.get("nature", "paying")
            qty = int(li.get("quantity", 0))
            if qty <= 0:
                continue
            tax = float(li.get("vat_rate_percent", 0))
            label = str(li.get("label", "Produit"))
            if nature == "paying":
                line_ht = float(li.get("line_ht", 0))
                ttc = round(line_ht * (1 + tax / 100.0), 2)
                positions.append(
                    {
                        "name": label,
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
        deposit_reference: str | None,
        currency: str = "EUR",
    ) -> VosFacturesInvoiceResult:
        positions = self._build_positions(lines)
        if not positions:
            raise ValueError("VosFactures : aucune ligne de facture à envoyer")

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
        dept = vosfactures_department_id()
        if dept is not None:
            inv["department_id"] = dept

        inv.update(self._build_buyer(pharmacy))

        if vosfactures_test_documents():
            inv["test"] = True

        if deposit_reference:
            inv["description"] = (
                (inv.get("description") or "").strip()
                + f"\nRéf. dépôt Digestic : {deposit_reference}"
            ).strip()

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
                "deposit_reference": deposit_reference,
            },
        }

        return VosFacturesInvoiceResult(
            provider=PROVIDER_KEY,
            external_id=str(ext_id) if ext_id is not None else None,
            invoice_number=str(num) if num else None,
            payload=enriched,
        )

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
