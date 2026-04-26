import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.db.models as orm
from app.db import mappers as mp
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self._db = db

    def _model_from_dict(self, data: dict) -> User:
        allowed = {
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        }
        clean = {k: v for k, v in data.items() if k in allowed}
        return User.from_dict(clean)

    def find_all(self) -> list[User]:
        rows = self._db.execute(select(orm.User)).scalars().all()
        return [mp.user_orm_to_domain(r) for r in rows]

    def find_by_id(self, id_: str) -> Optional[User]:
        try:
            uid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.User, uid)
        return mp.user_orm_to_domain(row) if row else None

    def find_by_email(self, email: str) -> Optional[User]:
        row = self._db.execute(
            select(orm.User).where(orm.User.email == email)
        ).scalar_one_or_none()
        return mp.user_orm_to_domain(row) if row else None

    def get_user_and_password_hash(
        self, email: str
    ) -> tuple[Optional[User], Optional[str]]:
        """Pour l’auth : utilisateur + hash bcrypt (hors modèle domaine)."""
        row = self._db.execute(
            select(orm.User).where(orm.User.email == email)
        ).scalar_one_or_none()
        if not row:
            return None, None
        h = row.password_hash
        return mp.user_orm_to_domain(row), h if h else None

    def find_by(self, **kwargs) -> list[User]:
        q = select(orm.User)
        for k, v in kwargs.items():
            q = q.where(getattr(orm.User, k) == v)
        rows = self._db.execute(q).scalars().all()
        return [mp.user_orm_to_domain(r) for r in rows]

    def find_by_role(self, role: str) -> list[User]:
        return self.find_by(role=role)

    def create(self, model: User) -> User:
        row = orm.User(
            id=mp.parse_uuid(model.id) if model.id else uuid.uuid4(),
            email=model.email,
            first_name=model.first_name,
            last_name=model.last_name,
            role=model.role,
            phone=model.phone,
            is_active=model.is_active,
        )
        self._db.add(row)
        self._db.flush()
        return mp.user_orm_to_domain(row)

    def update(self, id_: str, model: User) -> Optional[User]:
        try:
            uid = mp.parse_uuid(id_)
        except ValueError:
            return None
        row = self._db.get(orm.User, uid)
        if not row:
            return None
        row.email = model.email
        row.first_name = model.first_name
        row.last_name = model.last_name
        row.role = model.role
        row.phone = model.phone
        row.is_active = model.is_active
        self._db.flush()
        return mp.user_orm_to_domain(row)

    def delete(self, id_: str) -> bool:
        try:
            uid = mp.parse_uuid(id_)
        except ValueError:
            return False
        row = self._db.get(orm.User, uid)
        if not row:
            return False
        self._db.delete(row)
        return True
