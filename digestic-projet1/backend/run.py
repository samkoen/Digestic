"""
Lance l'API Uvicorn. Utilise toujours le venv `backend/.venv` s'il existe
(pour éviter "No module named 'sqlalchemy'" quand on tape `python run.py` avec le Python système).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_venv_python = (
    _root / ".venv" / "Scripts" / "python.exe"
    if sys.platform == "win32"
    else _root / ".venv" / "bin" / "python"
)

if _venv_python.is_file() and Path(sys.executable).resolve() != _venv_python.resolve():
    # Relancer le même script avec l'interpréteur du venv
    os.execv(
        str(_venv_python),
        [str(_venv_python), str(Path(__file__).resolve())] + sys.argv[1:],
    )

import uvicorn

if __name__ == "__main__":
    host = os.environ.get("UVICORN_HOST", "0.0.0.0")
    port = int(os.environ.get("UVICORN_PORT", os.environ.get("PORT", "5000")))
    print("\n=== Digestic API (FastAPI / Uvicorn) ===")
    print(f"  Ouvertures utiles depuis cette machine :")
    print(f"    http://127.0.0.1:{port}/docs   (Swagger)")
    print(f"    http://127.0.0.1:{port}/health  (sans base)")
    print(f"  Hôte configuré : {host}:{port}")
    print("========================================\n", flush=True)
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
