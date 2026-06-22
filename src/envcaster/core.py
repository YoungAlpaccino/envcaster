"""Typed reads from the environment with defaults, requirements, and clear errors."""

from __future__ import annotations

import builtins
import json as _json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, List, Mapping, Optional, Sequence, TypeVar

__all__ = [
    "Env",
    "EnvError",
    "MissingEnvError",
    "CastError",
    "ValidationError",
    "EnvValidationError",
    "env",
]

T = TypeVar("T")


class EnvError(Exception):
    """Base class for all envcaster errors."""


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


class ValidationError(EnvError, ValueError):
    """An environment variable parsed correctly but failed a constraint.

    Raised by ``choices=``, ``min=``, and ``max=``. Distinct from
    :class:`CastError`, which means the value could not be parsed at all.
    """

    def __init__(self, name: str, value: Any, reason: str) -> None:
        self.name = name
        self.value = value
        self.reason = reason
        super().__init__(f"Environment variable {name!r}={value!r} is invalid: {reason}.")


class EnvValidationError(EnvError):
    """Aggregates several errors collected from an :meth:`Env.collect` block."""

    def __init__(self, errors: Sequence[EnvError]) -> None:
        self.errors: List[EnvError] = list(errors)
        # Use args[0] for the clean message: KeyError's __str__ (inherited by
        # MissingEnvError) would otherwise wrap it in quotes.
        body = "\n".join(
            f"  - {exc.args[0] if exc.args else exc}" for exc in self.errors
        )
        n = len(self.errors)
        super().__init__(
            f"{n} environment variable error{'s' if n != 1 else ''} found:\n{body}"
        )


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
    variables raise :class:`MissingEnvError`; unparseable values raise
    :class:`CastError`; values that break a ``choices``/``min``/``max``
    constraint raise :class:`ValidationError`. All subclass :class:`EnvError`
    (and, where natural, the matching builtin), so you can catch broadly or
    narrowly.

    Use :meth:`collect` to validate a whole config block and report every
    problem at once instead of failing on the first.
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

    def _check_choices(self, name: str, value: Any, choices: Optional[Iterable[Any]]) -> None:
        if choices is None:
            return
        allowed = builtins.list(choices)
        if value not in allowed:
            shown = ", ".join(repr(c) for c in allowed)
            raise ValidationError(self._prefix + name, value, f"expected one of: {shown}")

    def _check_bounds(
        self, name: str, value: Any, min: Optional[Any], max: Optional[Any]
    ) -> None:
        if min is not None and value < min:
            raise ValidationError(self._prefix + name, value, f"must be >= {min!r}")
        if max is not None and value > max:
            raise ValidationError(self._prefix + name, value, f"must be <= {max!r}")

    # -- typed getters -----------------------------------------------------

    def str(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        choices: Optional[Iterable[str]] = None,
    ) -> str:
        """Return the variable as a string (the raw value, unchanged)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        self._check_choices(name, raw, choices)
        return raw

    def int(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[int] = None,
        max: Optional[int] = None,
        choices: Optional[Iterable[int]] = None,
    ) -> int:
        """Return the variable parsed as an ``int`` (base-10, whitespace ignored).

        Optionally constrain it with ``min``/``max`` bounds or a ``choices`` set.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            value = builtins.int(raw.strip())
        except ValueError:
            raise CastError(self._prefix + name, raw, "integer") from None
        self._check_choices(name, value, choices)
        self._check_bounds(name, value, min, max)
        return value

    def float(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[float] = None,
        max: Optional[float] = None,
        choices: Optional[Iterable[float]] = None,
    ) -> float:
        """Return the variable parsed as a ``float``.

        Optionally constrain it with ``min``/``max`` bounds or a ``choices`` set.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            value = builtins.float(raw.strip())
        except ValueError:
            raise CastError(self._prefix + name, raw, "float") from None
        self._check_choices(name, value, choices)
        self._check_bounds(name, value, min, max)
        return value

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
        choices: Optional[Iterable[T]] = None,
    ) -> T:
        """Apply an arbitrary ``func`` to the raw string value.

        Any exception from ``func`` is wrapped in :class:`CastError`. An optional
        ``choices`` set is checked against the converted value.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            value = func(raw)
        except Exception as exc:  # noqa: BLE001 - re-raised as CastError
            type_name = getattr(func, "__name__", "value")
            raise CastError(self._prefix + name, raw, type_name, hint=str(exc)) from None
        self._check_choices(name, value, choices)
        return value

    # -- batch validation --------------------------------------------------

    @contextmanager
    def collect(self) -> Iterator["Env"]:
        """Validate a whole config block, reporting *every* error at once.

        Inside the ``with`` block, getters that fail record their error and
        return ``None`` instead of raising, so the block runs to completion. On
        exit, if anything failed, a single :class:`EnvValidationError` is raised
        listing all problems::

            with env.collect() as cfg:
                PORT = cfg.int("PORT", default=8000)
                SECRET = cfg.str("SECRET_KEY", required=True)
                DB = cfg.str("DATABASE_URL", required=True)
            # If SECRET_KEY and DATABASE_URL are both missing, raises ONE error
            # naming both — not just the first.
        """
        collector = _Collector(self)
        yield collector
        if collector.errors:
            raise EnvValidationError(collector.errors)


class _Collector(Env):
    """An :class:`Env` that captures errors instead of raising (see ``collect``)."""

    def __init__(self, parent: Env) -> None:
        super().__init__(source=parent._source, prefix=parent._prefix)
        self.errors: List[EnvError] = []

    def _guard(self, method: str, args: tuple, kwargs: dict) -> Any:
        try:
            return getattr(super(), method)(*args, **kwargs)
        except EnvError as exc:
            self.errors.append(exc)
            return None

    def str(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("str", args, kwargs)

    def int(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("int", args, kwargs)

    def float(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("float", args, kwargs)

    def bool(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("bool", args, kwargs)

    def list(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("list", args, kwargs)

    def json(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("json", args, kwargs)

    def path(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("path", args, kwargs)

    def cast(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return self._guard("cast", args, kwargs)


# A ready-to-use instance bound to the live process environment.
env = Env()
