"""Crée la base 'digestic' sur le serveur indiqué par DATABASE_URL si elle n'existe pas."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2
from psycopg2 import sql

backend_dir = Path(__file__).resolve().parents[1]
load_dotenv(backend_dir / ".env")

url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL manquant", file=sys.stderr)
    sys.exit(1)

# postgresql://user:pass@host:port/dbname
last_slash = url.rfind("/")
if last_slash < 0:
    sys.exit(1)
name = url[last_slash + 1 :]
server_url = url[: last_slash + 1] + "postgres"

conn = psycopg2.connect(server_url)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
if cur.fetchone():
    print(f"Base '{name}' existe deja.")
else:
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    print(f"Base '{name}' creee.")
cur.close()
conn.close()
