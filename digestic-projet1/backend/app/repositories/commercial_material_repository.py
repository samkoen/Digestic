import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.commercial_material import CommercialMaterial


class CommercialMaterialRepository:
    def __init__(self, db: Session):
        self._db = db

    def _model_from_dict(self, data: dict) -> CommercialMaterial:
        return CommercialMaterial.from_dict(data)

    def find_all(self) -> list[CommercialMaterial]:
        rows = self._db.execute(select(orm.CommercialMaterial)).scalars().all()
        return [mp.material_orm_to_domain(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[CommercialMaterial]:
        try:
            mid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.CommercialMaterial, mid)
        return mp.material_orm_to_domain(row) if row else None

    def find_by(self, **kwargs) -> list[CommercialMaterial]:
        q = select(orm.CommercialMaterial)
        for k, v in kwargs.items():
            if hasattr(orm.CommercialMaterial, k):
                q = q.where(getattr(orm.CommercialMaterial, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.material_orm_to_domain(r) for r in rows]

    def find_active(self) -> list[CommercialMaterial]:
        q = select(orm.CommercialMaterial).where(orm.CommercialMaterial.is_active.is_(True))
        rows = self._db.execute(q).scalars().all()
        return [mp.material_orm_to_domain(r) for r in rows]

    def create(self, model: CommercialMaterial) -> CommercialMaterial:
        row = orm.CommercialMaterial(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            name=model.name,
            type=model.type,
            file_path=model.file_path,
            file_url=model.file_url,
            description=model.description,
            version=model.version,
            is_active=model.is_active,
        )
        self._db.add(row)
        self._db.flush()
        return mp.material_orm_to_domain(row)

    def update(self, id_: str, model: CommercialMaterial) -> Optional[CommercialMaterial]:
        try:
            mid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.CommercialMaterial, mid)
        if not row:
            return None
        row.name = model.name
        row.type = model.type
        row.file_path = model.file_path
        row.file_url = model.file_url
        row.description = model.description
        row.version = model.version
        row.is_active = model.is_active
        self._db.flush()
        return mp.material_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            mid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.CommercialMaterial, mid)
        if not row:
            return False
        self._db.delete(row)
        return True
