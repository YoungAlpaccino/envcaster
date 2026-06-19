"""A tiny, dependency-free ``.env`` reader.

Just enough to load a local ``.env`` in development. For complex needs
(variable interpolation, multiline values) reach for python-dotenv.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Union

__all__ = ["read_dotenv", "load_dotenv"]

_PathLike = Union[str, "os.PathLike[str]"]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def read_dotenv(path: _PathLike = ".env") -> Dict[str, str]:
    """Parse a ``.env`` file into a dict. Returns ``{}`` if the file is absent.

    Supports ``KEY=value``, ``export KEY=value``, ``#`` comments, blank lines,
    and single/double-quoted values. Does **not** touch ``os.environ``.
    """
    file = Path(path)
    if not file.is_file():
        return {}

    result: Dict[str, str] = {}
    for raw_line in file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        # Strip an inline comment only when the value is not quoted.
        stripped = value.strip()
        if stripped[:1] not in ("'", '"') and " #" in value:
            value = value.split(" #", 1)[0]
        result[key] = _unquote(value)
    return result


def load_dotenv(path: _PathLike = ".env", *, override: bool = False) -> Dict[str, str]:
    """Read a ``.env`` file and inject its values into ``os.environ``.

    By default existing environment variables win (``override=False``), so real
    environment configuration is never clobbered by the file. Returns the dict
    that was parsed from the file.
    """
    values = read_dotenv(path)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values
