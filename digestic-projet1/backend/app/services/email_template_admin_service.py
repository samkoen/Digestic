from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.domain.email_template_catalog import (
    EMAIL_TEMPLATE_CATALOG,
    catalog_entry_for_key,
)
from app.repositories.email_template_repository import EmailTemplateRepository

_KEY_SAFE = re.compile(r"^[a-z][a-z0-9_]{1,61}$")


def _row_to_public_dict(row, catalog_meta: dict | None) -> dict:
    d: dict = {
        "template_key": row.template_key,
        "subject_template": row.subject_template,
        "body_html_template": row.body_html_template,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if catalog_meta:
        d["label_fr"] = catalog_meta["label_fr"]
        d["description_fr"] = catalog_meta["description_fr"]
        d["placeholders"] = catalog_meta["placeholders"]
        d["catalog"] = catalog_meta.get("catalog", True)
    return d


class EmailTemplateAdminService:
    def __init__(self, db: Session):
        self._repo = EmailTemplateRepository(db)

    def get_one(self, template_key: str) -> dict | None:
        row = self._repo.find_by_key(template_key)
        if row is None:
            return None
        cat = catalog_entry_for_key(row.template_key)
        if cat:
            meta = {
                "label_fr": cat.label_fr,
                "description_fr": cat.description_fr,
                "placeholders": list(cat.placeholders),
                "catalog": True,
            }
        else:
            meta = {
                "label_fr": row.template_key.replace("_", " ").title(),
                "description_fr": "Modèle personnalisé",
                "placeholders": [],
                "catalog": False,
            }
        return _row_to_public_dict(row, meta)

    def list_all(self) -> list[dict]:
        rows = self._repo.list_ordered()
        out = []
        for row in rows:
            cat = catalog_entry_for_key(row.template_key)
            if cat:
                meta = {
                    "label_fr": cat.label_fr,
                    "description_fr": cat.description_fr,
                    "placeholders": list(cat.placeholders),
                    "catalog": True,
                }
            else:
                meta = {
                    "label_fr": row.template_key.replace("_", " ").title(),
                    "description_fr": "Modèle personnalisé",
                    "placeholders": [],
                    "catalog": False,
                }
            out.append(_row_to_public_dict(row, meta))
        return out

    def catalog_only(self) -> list[dict]:
        """Liste des types documentés dans le catalogue (avec placeholders), sans données éditées."""
        return [
            {
                "template_key": e.key,
                "label_fr": e.label_fr,
                "description_fr": e.description_fr,
                "placeholders": list(e.placeholders),
            }
            for e in EMAIL_TEMPLATE_CATALOG
        ]

    def create_custom(
        self,
        *,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        admin_user_id: str | None,
    ) -> dict:
        key = str(template_key).strip().lower()
        if not _KEY_SAFE.match(key):
            raise ValueError(
                "Clé invalide : utiliser snake_case ASCII (lettres minuscules, chiffres, tirets bas)"
            )
        if self._repo.find_by_key(key):
            raise ValueError(f"Une entrée existe déjà pour « {key} »")
        if catalog_entry_for_key(key):
            raise ValueError(
                "Cette clé est réservée au catalogue officiel ; modifiez l’entrée existante au lieu de la recréer"
            )

        uid = uuid.UUID(admin_user_id) if admin_user_id else None
        row = self._repo.create(key, subject_template.strip(), body_html_template, uid)
        return _row_to_public_dict(
            row,
            {
                "label_fr": row.template_key.replace("_", " ").title(),
                "description_fr": "Modèle personnalisé",
                "placeholders": [],
            },
        )

    def update_existing(
        self,
        *,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        admin_user_id: str | None,
    ) -> dict | None:
        key = str(template_key).strip()
        uid = uuid.UUID(admin_user_id) if admin_user_id else None
        row = self._repo.update_content(
            key,
            subject_template.strip(),
            body_html_template.strip(),
            uid,
        )
        if row is None:
            return None
        return self.get_one(key)
