"""Typed reads from the environment with defaults, requirements, and clear errors."""

from __future__ import annotations

import builtins
import json as _json
import os
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional, TypeVar

__all__ = [
    "Env",
    "EnvError",
    "MissingEnvError",
    "CastError",
    "env",
]

T = TypeVar("T")


class EnvError(Exception):
    """Base class for all envcast errors."""


class MissingEnvError(EnvError, KeyError):
    """A required environment variable was not set."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Required environment variable {name!r} is not set.")


class CastError(EnvError, ValueError):
    """An environment variable could not be cast to the requested type."""

    def __init__(self, name: str, value: str, type_name: str, hint: str = "") -> None:
        self.name = name
        self.value = value
        self.type_name = type_name
        msg = f"Environment variable {name!r}={value!r} is not a valid {type_name}."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)


# Sentinels — distinct from any user value (including None).
class _Unset:
    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return "<unset>"


_UNSET: Any = _Unset()
_USE_DEFAULT: Any = object()

_TRUE = {"1", "true", "t", "yes", "y", "on"}
_FALSE = {"0", "false", "f", "no", "n", "off"}


class Env:
    """A typed reader over a mapping of environment variables.

    By default it reads the live process environment (``os.environ``). Pass a
    ``source`` mapping (e.g. a plain ``dict``) to read from somewhere else —
    handy in tests. A ``prefix`` is prepended to every name you look up, so
    ``Env(prefix="APP_").int("PORT")`` reads ``APP_PORT``.

    A variable is **required unless you pass a ``default``**. Missing required
    variables raise :class:`MissingEnvError`; bad values raise :class:`CastError`.
    Both subclass :class:`EnvError` (and the matching builtin), so you can catch
    broadly or narrowly.
    """

    def __init__(
        self,
        source: Optional[Mapping[str, str]] = None,
        *,
        prefix: str = "",
    ) -> None:
        self._source = source
        self._prefix = prefix

    # -- internals ---------------------------------------------------------

    def _mapping(self) -> Mapping[str, str]:
        # Read os.environ lazily so changes after construction are seen.
        return os.environ if self._source is None else self._source

    def _raw(self, name: str, default: Any, required: bool) -> str:
        key = self._prefix + name
        value = self._mapping().get(key)
        if value is None:
            if required or default is _UNSET:
                raise MissingEnvError(key)
            return _USE_DEFAULT
        return value

    # -- typed getters -----------------------------------------------------

    def str(self, name: str, default: Any = _UNSET, *, required: bool = False) -> str:
        """Return the variable as a string (the raw value, unchanged)."""
        raw = self._raw(name, default, required)
        return default if raw is _USE_DEFAULT else raw

    def int(self, name: str, default: Any = _UNSET, *, required: bool = False) -> int:
        """Return the variable parsed as an ``int`` (base-10, whitespace ignored)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            return int(raw.strip())
        except ValueError:
            raise CastError(self._prefix + name, raw, "integer") from None

    def float(self, name: str, default: Any = _UNSET, *, required: bool = False) -> float:
        """Return the variable parsed as a ``float``."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            return float(raw.strip())
        except ValueError:
            raise CastError(self._prefix + name, raw, "float") from None

    def bool(self, name: str, default: Any = _UNSET, *, required: bool = False) -> bool:
        """Return the variable as a ``bool``.

        Truthy: ``1 true t yes y on``. Falsy: ``0 false f no n off``
        (case-insensitive). Anything else raises :class:`CastError`.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        token = raw.strip().lower()
        if token in _TRUE:
            return True
        if token in _FALSE:
            return False
        raise CastError(
            self._prefix + name,
            raw,
            "boolean",
            hint=f"Use one of: {', '.join(sorted(_TRUE | _FALSE))}.",
        )

    def list(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        sep: str = ",",
        cast: Callable[[str], T] = builtins.str,  # type: ignore[assignment]
        required: bool = False,
    ) -> List[T]:
        """Split the variable on ``sep`` into a list.

        Items are stripped of surrounding whitespace and empty items dropped.
        Pass ``cast`` to convert each item (e.g. ``cast=int``).
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        items = [piece.strip() for piece in raw.split(sep)]
        items = [piece for piece in items if piece]
        try:
            return [cast(piece) for piece in items]
        except (ValueError, TypeError):
            raise CastError(self._prefix + name, raw, "list", hint="An item failed to cast.") from None

    def json(self, name: str, default: Any = _UNSET, *, required: bool = False) -> Any:
        """Parse the variable as JSON and return the resulting object."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            return _json.loads(raw)
        except _json.JSONDecodeError:
            raise CastError(self._prefix + name, raw, "JSON") from None

    def path(self, name: str, default: Any = _UNSET, *, required: bool = False) -> Path:
        """Return the variable as a :class:`pathlib.Path` (not resolved/validated)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        return Path(raw)

    def cast(
        self,
        name: str,
        func: Callable[[str], T],
        default: Any = _UNSET,
        *,
        required: bool = False,
    ) -> T:
        """Apply an arbitrary ``func`` to the raw string value.

        Any exception from ``func`` is wrapped in :class:`CastError`.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            return func(raw)
        except Exception as exc:  # noqa: BLE001 - re-raised as CastError
            type_name = getattr(func, "__name__", "value")
            raise CastError(self._prefix + name, raw, type_name, hint=str(exc)) from None


# A ready-to-use instance bound to the live process environment.
env = Env()
