"""Fixtures pour tests d'intégration (HTTP + PostgreSQL, transaction rollback)."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from app.db import session as db_session_module
from app.dependencies import get_db


def _load_test_env_file() -> None:
    """``backend/.env.test`` si présent (ne charge pas au collect des UT seuls)."""
    backend_dir = Path(__file__).resolve().parents[2]
    env_test = backend_dir / ".env.test"
    if env_test.is_file():
        load_dotenv(env_test, override=True)


def _require_database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        pytest.skip(
            "DATABASE_URL non défini — exécuter avec une base de test "
            "(même schéma qu’en prod, ex. alembic upgrade head)."
        )
    return url


@pytest.fixture(scope="session")
def integration_engine():
    _load_test_env_file()
    db_session_module.reset_engine()
    _require_database_url()
    return db_session_module.get_engine()


@pytest.fixture
def db_session(integration_engine) -> Generator[Session, None, None]:
    conn = integration_engine.connect()
    trans = conn.begin()
    SessionTesting = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=conn,
        expire_on_commit=False,
    )
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Client FastAPI avec session SQLAlchemy partagée et rollback (pas de commit réel)."""

    def override_get_db():
        yield db_session

    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def no_transactional_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """Évite envoi d’e-mails pendant la facturation (tests d’intégration)."""
    monkeypatch.setattr(
        "app.services.delivery_note_service.notification_email_for_pharmacy",
        lambda _p: "",
    )
