"""Dépendances FastAPI partagées."""
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import get_db as get_db_session


def get_db() -> Generator[Session, None, None]:
    """Session SQLAlchemy (une transaction par requête)."""
    yield from get_db_session()
