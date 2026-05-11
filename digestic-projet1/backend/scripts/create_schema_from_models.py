"""
Crée le schéma PostgreSQL à partir des modèles SQLAlchemy (``Base.metadata``).

À utiliser uniquement sur une base **vide** (ex. ``digestic_test``).

Après exécution, aligner Alembic sans rejouer les migrations::

    $env:DIGESTIC_ENV = "test"   # si tu utilises .env.test
    alembic stamp head

Sans ``stamp head``, un ``alembic upgrade head`` tenterait de recréer des objets déjà là.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

load_dotenv(backend_dir / ".env")
if os.environ.get("DIGESTIC_ENV", "").strip().lower() == "test":
    load_dotenv(backend_dir / ".env.test", override=True)

from app.db.base import Base  # noqa: E402
import app.db.models  # noqa: F401, E402


def main() -> None:
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        print("DATABASE_URL manquant (.env ou DIGESTIC_ENV=test + .env.test).", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(url)
    with engine.connect() as conn:
        n = conn.execute(
            text(
                "select count(*) from information_schema.tables "
                "where table_schema = 'public' and table_type = 'BASE TABLE'"
            )
        ).scalar_one()
        if int(n) > 0:
            print(
                "Refus: la base public contient déjà des tables. "
                "Vide la base ou utilise alembic upgrade head.",
                file=sys.stderr,
            )
            sys.exit(2)

    Base.metadata.create_all(bind=engine)
    print("Schéma créé via Base.metadata.create_all().")
    print('Ensuite: alembic stamp head  (même DATABASE_URL / DIGESTIC_ENV).')


if __name__ == "__main__":
    main()
