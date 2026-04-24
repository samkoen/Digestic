import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.visit import Visit


class VisitRepository:
    def __init__(self, db: Session):
        self._db = db

    def find_all(self) -> list[Visit]:
        rows = self._db.execute(select(orm.Visit)).scalars().all()
        return [mp.visit_orm_to_domain(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[Visit]:
        try:
            vid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Visit, vid)
        return mp.visit_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[Visit]:
        q = select(orm.Visit)
        for k, v in kwargs.items():
            c = k
            if k == "pharmacy_id" or k == "commercial_id":
                v = mp.parse_uuid(v) if v else v
            q = q.where(getattr(orm.Visit, c) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.visit_orm_to_domain(r) for r in rows]

    def find_by_commercial(self, commercial_id: str) -> list[Visit]:
        return self.find_by(commercial_id=commercial_id)

    def find_by_pharmacy(self, pharmacy_id: str) -> list[Visit]:
        return self.find_by(pharmacy_id=pharmacy_id)

    def find_by_status(self, status: str) -> list[Visit]:
        return self.find_by(status=status)

    def create(self, model: Visit) -> Visit:
        row = orm.Visit(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            pharmacy_id=mp.parse_uuid(model.pharmacy_id),
            commercial_id=mp.parse_uuid(model.commercial_id),
            scheduled_date=mp.parse_date(model.scheduled_date),
            scheduled_time=mp.parse_time_hm(model.scheduled_time) if model.scheduled_time else None,
            status=model.status,
            notes=model.notes,
        )
        self._db.add(row)
        self._db.flush()
        return mp.visit_orm_to_domain(row)

    def update(self, id_: str, model: Visit) -> Optional[Visit]:
        try:
            vid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.Visit, vid)
        if not row:
            return None
        row.pharmacy_id = mp.parse_uuid(model.pharmacy_id)
        row.commercial_id = mp.parse_uuid(model.commercial_id)
        row.scheduled_date = mp.parse_date(model.scheduled_date)
        row.scheduled_time = mp.parse_time_hm(model.scheduled_time) if model.scheduled_time else None
        row.status = model.status
        row.notes = model.notes
        self._db.flush()
        return mp.visit_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            vid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.Visit, vid)
        if not row:
            return False
        self._db.delete(row)
        return True
