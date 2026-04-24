"""
Données initiales après installation (entrepôt par défaut, compte admin).

Exécuter depuis le dossier `backend/` (la base et les migrations doivent déjà exister) :

1) Modes recommandés (le mot de passe n’apparaît pas en clair dans l’historique) :

   PowerShell :
     $env:INSTALL_ADMIN_EMAIL="admin@votredomaine.fr"
     $env:INSTALL_ADMIN_PASSWORD="votre_mot_de_passe"
     .\\.venv\\Scripts\\python.exe scripts/seed_install.py

   bash :
     export INSTALL_ADMIN_EMAIL="admin@votredomaine.fr"
     export INSTALL_ADMIN_PASSWORD="votre_mot_de_passe"
     python scripts/seed_install.py

2) Arguments (pratique en dev, moins discret) :

   python scripts/seed_install.py --admin-email admin@exemple.com --admin-password "VotreMotDePasse"

3) Avec prénom / nom affichés :

   python scripts/seed_install.py --admin-email a@a.fr --admin-password "xxx" --first-name "Admin" --last-name "Principal"

   Si l’utilisateur admin (même e-mail) existe déjà, le script ne fait rien (code sortie 0),
   sauf avec --update-password pour remplacer uniquement le hachage du mot de passe.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# exécution : `python scripts/seed_install.py` depuis `backend/`
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session

load_dotenv(_BACKEND / ".env")

from app.core.security import hash_password
from app.db import models as orm
from app.db.bootstrap import get_or_create_default_warehouse_id
import app.db.session as session_mod


def _session() -> Session:
    # Ne pas `from app.db.session import SessionLocal` : au chargement, SessionLocal
    # vaut None ; get_engine() réassigne l’attribut sur le module, pas une variable importée.
    session_mod.get_engine()
    if session_mod.SessionLocal is None:
        raise RuntimeError("Session non initialisée (DATABASE_URL manquant ?)")
    return session_mod.SessionLocal()


def ensure_default_warehouse(db: Session) -> None:
    get_or_create_default_warehouse_id(db)
    print("[OK] Entrepot par defaut verifie/creé.")


def ensure_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    update_password: bool,
) -> None:
    email = email.strip().lower()
    row = db.execute(select(orm.User).where(orm.User.email == email)).scalar_one_or_none()
    pwd_hash = hash_password(password)
    if row is None:
        u = orm.User(
            email=email,
            password_hash=pwd_hash,
            first_name=first_name,
            last_name=last_name,
            role="admin",
            is_active=True,
        )
        db.add(u)
        print(f"[OK] Utilisateur admin créé : {email}")
    else:
        if row.role != "admin":
            row.role = "admin"
            print(f"[OK] Rôle de {email} passé en admin.")
        if update_password:
            row.password_hash = pwd_hash
            print(f"[OK] Mot de passe mis à jour pour {email}.")
        else:
            print(f"[i] L'utilisateur {email} existe déjà. Rien d'autre à faire. (--update-password pour le MDP)")


def main() -> int:
    p = argparse.ArgumentParser(description="Peuplement initial (entrepot + admin).")
    p.add_argument(
        "--admin-email",
        help="E-mail admin (ou variable INSTALL_ADMIN_EMAIL).",
    )
    p.add_argument(
        "--admin-password",
        help="Mot de passe admin (ou INSTALL_ADMIN_PASSWORD).",
    )
    p.add_argument("--first-name", default="Admin", help="Prénom (défaut: Admin).")
    p.add_argument("--last-name", default="Système", help="Nom (défaut: Système).")
    p.add_argument(
        "--update-password",
        action="store_true",
        help="Si l’utilisateur existe, remplace uniquement le hachage du mot de passe.",
    )
    args = p.parse_args()

    email = (args.admin_email or os.environ.get("INSTALL_ADMIN_EMAIL", "")).strip()
    password = args.admin_password or os.environ.get("INSTALL_ADMIN_PASSWORD", "")

    if not email or not password:
        print(
            "Erreur : définis INSTALL_ADMIN_EMAIL et INSTALL_ADMIN_PASSWORD "
            "ou passes --admin-email et --admin-password.\n"
            "Voir la doc en tête de ce fichier (scripts/seed_install.py).",
            file=sys.stderr,
        )
        return 1

    db = _session()
    try:
        ensure_default_warehouse(db)
        ensure_admin_user(
            db,
            email=email,
            password=password,
            first_name=args.first_name,
            last_name=args.last_name,
            update_password=args.update_password,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erreur : {e}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print("Terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
