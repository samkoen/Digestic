from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm


class EmailTemplateRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_ordered(self) -> list[orm.EmailTemplate]:
        return list(
            self._db.execute(
                select(orm.EmailTemplate).order_by(orm.EmailTemplate.template_key.asc())
            ).scalars()
        )

    def find_by_key(self, template_key: str) -> orm.EmailTemplate | None:
        return self._db.execute(
            select(orm.EmailTemplate).where(
                orm.EmailTemplate.template_key == str(template_key).strip()
            )
        ).scalar_one_or_none()

    def create(
        self,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        admin_user_id: uuid.UUID | None,
    ) -> orm.EmailTemplate:
        row = orm.EmailTemplate(
            template_key=str(template_key).strip(),
            subject_template=subject_template,
            body_html_template=body_html_template,
            updated_by_user_id=admin_user_id,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def update_content(
        self,
        template_key: str,
        subject_template: str,
        body_html_template: str,
        admin_user_id: uuid.UUID | None,
    ) -> orm.EmailTemplate | None:
        row = self.find_by_key(template_key)
        if row is None:
            return None
        row.subject_template = subject_template
        row.body_html_template = body_html_template
        row.updated_by_user_id = admin_user_id
        self._db.flush()
        return row
