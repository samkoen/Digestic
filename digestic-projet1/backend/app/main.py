"""Application FastAPI : entrée principale du backend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import SECRET_KEY

from app.controllers import (
    auth_controller,
    commercial_material_controller,
    credit_note_controller,
    delivery_note_controller,
    depot_controller,
    email_template_controller,
    invoice_controller,
    pharmacy_advanced_filter_controller,
    pharmacy_controller,
    planning_controller,
    product_controller,
    table_view_controller,
    user_controller,
    visit_controller,
    visit_report_controller,
)

logger = logging.getLogger(__name__)


def _bootstrap_database_sync():
    """Peut prendre plusieurs secondes si PostgreSQL est lent ou injoignable — ne doit pas retarder HTTP."""
    try:
        from app.db import bootstrap
        import app.db.session as db_session

        db_session.get_engine()
        maker = db_session.SessionLocal
        if maker is None:
            logger.error(
                "Session factory non initialisée après get_engine() — vérifiez DATABASE_URL et session.py."
            )
            return
        db = maker()
        try:
            try:
                bootstrap.get_or_create_default_warehouse_id(db)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Entrepôt par défaut : échec (PostgreSQL disponible ? migrations OK ?)."
                )

            try:
                bootstrap.ensure_builtin_email_templates(db)
                db.commit()
            except ProgrammingError as e:
                detail = str(e.orig) if getattr(e, "orig", None) else str(e)
                logger.warning(
                    "Table modèles e-mail absente ou schéma non à jour (%s). alembic upgrade head.",
                    detail,
                )
                db.rollback()
            except SQLAlchemyError as e:
                logger.warning("Modèles e-mail non initialisés (%s).", e)
                db.rollback()
        finally:
            db.close()
    except Exception:
        logger.exception(
            "Bootstrap Digestic incomplet (.env DATABASE_URL ou dépendances). "
            "L’application tourne tout de même (GET /health, login…) ; la base doit être réparée."
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Répond HTTP tout de suite ; le bootstrap DB tourne dans un thread (évite blocage Postgres au démarrage)."""
    asyncio.create_task(asyncio.to_thread(_bootstrap_database_sync))
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Digestic API",
        redirect_slashes=False,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        max_age=60 * 60 * 24 * 31,
        same_site="lax",
        https_only=False,
    )

    @app.get("/health", tags=["health"])
    def health_check():
        """Vérifie que le serveur HTTP répond (sans base de données)."""
        return {"status": "ok"}

    app.include_router(auth_controller.router, prefix="/api/auth", tags=["auth"])
    app.include_router(pharmacy_controller.router, prefix="/api/pharmacies", tags=["pharmacies"])
    app.include_router(
        pharmacy_advanced_filter_controller.router,
        prefix="/api/pharmacy-advanced-filters",
        tags=["pharmacy-advanced-filters"],
    )
    app.include_router(product_controller.router, prefix="/api/products", tags=["products"])
    app.include_router(depot_controller.router, prefix="/api/depots", tags=["depots"])
    app.include_router(visit_controller.router, prefix="/api/visits", tags=["visits"])
    app.include_router(
        planning_controller.router, prefix="/api/planning", tags=["planning"]
    )
    app.include_router(visit_report_controller.router, prefix="/api/visit-reports", tags=["visit-reports"])
    app.include_router(delivery_note_controller.router, prefix="/api/delivery-notes", tags=["delivery-notes"])
    app.include_router(invoice_controller.router, prefix="/api/invoices", tags=["invoices"])
    app.include_router(
        credit_note_controller.router,
        prefix="/api/credit-notes",
        tags=["credit-notes"],
    )
    app.include_router(commercial_material_controller.router, prefix="/api/commercial-materials", tags=["commercial-materials"])
    app.include_router(user_controller.router, prefix="/api/users", tags=["users"])
    app.include_router(
        table_view_controller.router,
        prefix="/api/table-views",
        tags=["table-views"],
    )
    app.include_router(
        email_template_controller.router,
        prefix="/api/admin/email-templates",
        tags=["admin-email-templates"],
    )

    backend_dir = Path(__file__).resolve().parent.parent
    uploads_dir = backend_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    (uploads_dir / "visit_reports").mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    return app


app = create_app()
