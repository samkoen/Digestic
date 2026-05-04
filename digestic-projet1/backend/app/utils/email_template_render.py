"""Interpolation `{{ placeholder }}` dans sujet et corps HTML."""

from __future__ import annotations

import re
from typing import Any, Mapping

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*\}\}")


def interpolate_template(template: str, variables: Mapping[str, Any]) -> str:
    def _repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in variables:
            return m.group(0)
        val = variables[key]
        if val is None:
            return ""
        return str(val)

    return _PLACEHOLDER_RE.sub(_repl, template)
