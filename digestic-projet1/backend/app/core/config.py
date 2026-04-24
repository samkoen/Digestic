"""Configuration partagée (chemins, secrets) — indépendante du framework web."""
import os

from dotenv import load_dotenv

# backend/ = parent de app/
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

DATA_DIR = os.path.join(_BACKEND_DIR, "data")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
