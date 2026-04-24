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
    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=True)
