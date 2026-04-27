"""Application FastAPI : entrée principale du backend."""
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import SECRET_KEY
from app.controllers import (
    auth_controller,
    commercial_material_controller,
    delivery_note_controller,
    depot_controller,
    invoice_controller,
    pharmacy_controller,
    product_controller,
    table_view_controller,
    user_controller,
    visit_controller,
    visit_report_controller,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.db import bootstrap
    from app.db.session import SessionLocal, get_engine

    get_engine()
    if SessionLocal is not None:
        db = SessionLocal()
        try:
            bootstrap.get_or_create_default_warehouse_id(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
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

    app.include_router(auth_controller.router, prefix="/api/auth", tags=["auth"])
    app.include_router(pharmacy_controller.router, prefix="/api/pharmacies", tags=["pharmacies"])
    app.include_router(product_controller.router, prefix="/api/products", tags=["products"])
    app.include_router(depot_controller.router, prefix="/api/depots", tags=["depots"])
    app.include_router(visit_controller.router, prefix="/api/visits", tags=["visits"])
    app.include_router(visit_report_controller.router, prefix="/api/visit-reports", tags=["visit-reports"])
    app.include_router(delivery_note_controller.router, prefix="/api/delivery-notes", tags=["delivery-notes"])
    app.include_router(invoice_controller.router, prefix="/api/invoices", tags=["invoices"])
    app.include_router(commercial_material_controller.router, prefix="/api/commercial-materials", tags=["commercial-materials"])
    app.include_router(user_controller.router, prefix="/api/users", tags=["users"])
    app.include_router(
        table_view_controller.router,
        prefix="/api/table-views",
        tags=["table-views"],
    )

    backend_dir = Path(__file__).resolve().parent.parent
    uploads_dir = backend_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    (uploads_dir / "visit_reports").mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    return app


app = create_app()
