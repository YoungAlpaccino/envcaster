"""A tiny, dependency-free ``.env`` reader.

Just enough to load a local ``.env`` in development. For complex needs
(multiline values, advanced shell semantics) reach for python-dotenv.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Union

__all__ = [
    "read_dotenv",
    "load_dotenv",
    "find_dotenv",
    "load_layered",
    "load_stack",
]

_PathLike = Union[str, "os.PathLike[str]"]

# ${NAME} or $NAME references, used only when interpolate=True.
_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _interpolate(value: str, context: Mapping[str, str]) -> str:
    def replace(match: "re.Match[str]") -> str:
        name = match.group(1) or match.group(2)
        return context.get(name, "")

    # Honor a backslash escape: \$ stays a literal dollar sign.
    parts = value.split(r"\$")
    return "$".join(_VAR_RE.sub(replace, part) for part in parts)


def read_dotenv(path: _PathLike = ".env", *, interpolate: bool = False) -> Dict[str, str]:
    """Parse a ``.env`` file into a dict. Returns ``{}`` if the file is absent.

    Supports ``KEY=value``, ``export KEY=value``, ``#`` comments, blank lines,
    and single/double-quoted values. Does **not** touch ``os.environ``.

    With ``interpolate=True``, ``${VAR}`` / ``$VAR`` references inside unquoted
    or double-quoted values are expanded from earlier keys in the same file and
    then from ``os.environ`` (unknown references become empty). Single-quoted
    values are always literal, and ``\\$`` is a literal dollar sign.
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
        quote = stripped[:1]
        if quote not in ("'", '"') and " #" in value:
            value = value.split(" #", 1)[0]
        text = _unquote(value)
        if interpolate and quote != "'":
            text = _interpolate(text, {**os.environ, **result})
        result[key] = text
    return result


def load_dotenv(
    path: _PathLike = ".env", *, override: bool = False, interpolate: bool = False
) -> Dict[str, str]:
    """Read a ``.env`` file and inject its values into ``os.environ``.

    By default existing environment variables win (``override=False``), so real
    environment configuration is never clobbered by the file. Pass
    ``interpolate=True`` to expand ``${VAR}`` references (see :func:`read_dotenv`).
    Returns the dict that was parsed from the file.
    """
    values = read_dotenv(path, interpolate=interpolate)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values


def find_dotenv(
    filename: str = ".env", *, start: Optional[_PathLike] = None, usecwd: bool = False
) -> str:
    """Search for ``filename`` from ``start`` upward to the filesystem root.

    Returns the first match as a string path, or ``""`` if none is found. By
    default the search begins at the current working directory; pass ``start``
    to begin elsewhere. Great for finding the project ``.env`` no matter which
    subdirectory the process was launched from.
    """
    here = Path(os.getcwd() if usecwd or start is None else start).resolve()
    for directory in (here, *here.parents):
        candidate = directory / filename
        if candidate.is_file():
            return str(candidate)
    return ""


def load_layered(
    paths: Iterable[_PathLike],
    *,
    override_env: bool = False,
    interpolate: bool = False,
) -> Dict[str, str]:
    """Load several ``.env`` files in order, later files winning over earlier.

    Files are merged into one mapping (so ``.env.local`` overrides ``.env``),
    then injected into ``os.environ``. Real environment variables still win
    unless ``override_env=True``. Missing files are skipped. Returns the merged
    mapping that was applied.
    """
    merged: Dict[str, str] = {}
    for path in paths:
        merged.update(read_dotenv(path, interpolate=interpolate))
    for key, value in merged.items():
        if override_env or key not in os.environ:
            os.environ[key] = value
    return merged


def load_stack(
    stage: Optional[str] = None,
    *,
    root: _PathLike = ".",
    override_env: bool = False,
    interpolate: bool = True,
) -> Dict[str, str]:
    """Load a conventional stack of ``.env`` files for the given ``stage``.

    Loads (lowest to highest precedence)::

        .env  <  .env.<stage>  <  .env.local  <  .env.<stage>.local

    so stage- and machine-specific overrides layer cleanly on top of committed
    defaults. ``stage`` is typically something like ``"dev"`` or ``"prod"``.
    """
    base = Path(root)
    names: List[str] = [".env"]
    if stage:
        names.append(f".env.{stage}")
    names.append(".env.local")
    if stage:
        names.append(f".env.{stage}.local")
    return load_layered(
        [base / name for name in names],
        override_env=override_env,
        interpolate=interpolate,
    )
