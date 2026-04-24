import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None
SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine, SessionLocal
    if _engine is not None:
        return _engine
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (e.g. in backend/.env)")
    _engine = create_engine(
        url,
        echo=os.environ.get("SQL_ECHO", "").lower() in ("1", "true", "yes"),
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=_engine, expire_on_commit=False
    )
    return _engine


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : une transaction par requête (commit si succès)."""
    if SessionLocal is None:
        get_engine()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
