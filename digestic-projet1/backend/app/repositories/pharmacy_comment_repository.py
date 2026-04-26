import uuid
from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.pharmacy_comment import PharmacyComment as PharmacyCommentModel


def _row_to_domain(row: orm.PharmacyComment) -> PharmacyCommentModel:
    return PharmacyCommentModel(
        id=str(row.id),
        pharmacy_id=str(row.pharmacy_id),
        text=row.body,
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


class PharmacyCommentRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_by_pharmacy(self, pharmacy_id: str) -> List[PharmacyCommentModel]:
        try:
            pid = mp.parse_uuid(pharmacy_id)
        except ValueError:
            return []
        q = (
            select(orm.PharmacyComment)
            .where(orm.PharmacyComment.pharmacy_id == pid)
            .order_by(desc(orm.PharmacyComment.created_at))
        )
        rows = self._db.execute(q).scalars().all()
        return [_row_to_domain(r) for r in rows]

    def create(self, pharmacy_id: str, text: str) -> Optional[PharmacyCommentModel]:
        try:
            pid = mp.parse_uuid(pharmacy_id)
        except ValueError:
            return None
        row = orm.PharmacyComment(
            id=uuid.uuid4(),
            pharmacy_id=pid,
            body=(text or "").strip(),
        )
        if not row.body:
            return None
        self._db.add(row)
        self._db.flush()
        return _row_to_domain(row)

    def delete(self, pharmacy_id: str, comment_id: str) -> bool:
        try:
            pid = mp.parse_uuid(pharmacy_id)
            cid = mp.parse_uuid(comment_id)
        except ValueError:
            return False
        row = self._db.get(orm.PharmacyComment, cid)
        if not row or row.pharmacy_id != pid:
            return False
        self._db.delete(row)
        self._db.flush()
        return True
