"""Typed reads from the environment with defaults, requirements, and clear errors."""

from __future__ import annotations

import base64
import builtins
import datetime as _dt
import json as _json
import os
import re
import urllib.parse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, List, Mapping, Optional, Sequence, TypeVar

from envcaster.secret import Secret

__all__ = [
    "Env",
    "Secret",
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

# Duration: a bare number is seconds; otherwise a run of <number><unit> tokens.
_DURATION_UNITS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0, "d": 86400.0, "w": 604800.0}
_DURATION_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s|m|h|d|w)", re.IGNORECASE)


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

    def decimal(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[Decimal] = None,
        max: Optional[Decimal] = None,
        choices: Optional[Iterable[Decimal]] = None,
    ) -> Decimal:
        """Return the variable as a :class:`decimal.Decimal` (exact precision)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            value = Decimal(raw.strip())
        except InvalidOperation:
            raise CastError(self._prefix + name, raw, "decimal") from None
        self._check_choices(name, value, choices)
        self._check_bounds(name, value, min, max)
        return value

    def duration(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[_dt.timedelta] = None,
        max: Optional[_dt.timedelta] = None,
    ) -> _dt.timedelta:
        """Return the variable as a :class:`datetime.timedelta`.

        A bare number is seconds (``"30"`` -> 30s). Otherwise a run of
        ``<number><unit>`` tokens is summed, where unit is one of
        ``ms s m h d w`` (e.g. ``"500ms"``, ``"5m"``, ``"1h30m"``, ``"2d"``).
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        text = raw.strip()
        seconds: Optional[float] = None
        if text:
            try:
                seconds = builtins.float(text)
            except ValueError:
                pos, total, matched = 0, 0.0, False
                for m in _DURATION_TOKEN.finditer(text):
                    if m.start() != pos:
                        break
                    total += builtins.float(m.group(1)) * _DURATION_UNITS[m.group(2).lower()]
                    pos, matched = m.end(), True
                if matched and pos == len(text):
                    seconds = total
        if seconds is None:
            raise CastError(
                self._prefix + name,
                raw,
                "duration",
                hint="Use seconds, or forms like '500ms', '5m', '1h30m', '2d'.",
            )
        value = _dt.timedelta(seconds=seconds)
        self._check_bounds(name, value, min, max)
        return value

    def datetime(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[_dt.datetime] = None,
        max: Optional[_dt.datetime] = None,
    ) -> _dt.datetime:
        """Parse the variable as an ISO 8601 datetime (a trailing ``Z`` is UTC)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        text = raw.strip()
        iso = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            value = _dt.datetime.fromisoformat(iso)
        except ValueError:
            raise CastError(self._prefix + name, raw, "ISO 8601 datetime") from None
        self._check_bounds(name, value, min, max)
        return value

    def date(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        min: Optional[_dt.date] = None,
        max: Optional[_dt.date] = None,
    ) -> _dt.date:
        """Parse the variable as an ISO 8601 date (``YYYY-MM-DD``)."""
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        try:
            value = _dt.date.fromisoformat(raw.strip())
        except ValueError:
            raise CastError(self._prefix + name, raw, "ISO 8601 date") from None
        self._check_bounds(name, value, min, max)
        return value

    def bytes(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        encoding: str = "utf-8",
    ) -> bytes:
        """Return the variable as ``bytes``.

        ``encoding`` is either a text codec (default ``"utf-8"``) or one of the
        binary decoders ``"base64"`` / ``"hex"`` for keys and secrets.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        enc = encoding.lower()
        try:
            if enc == "base64":
                return base64.b64decode(raw.strip(), validate=True)
            if enc == "hex":
                return builtins.bytes.fromhex(raw.strip())
            return raw.encode(encoding)
        except (ValueError, LookupError) as exc:
            raise CastError(self._prefix + name, raw, f"{encoding} bytes", hint=str(exc)) from None

    def url(
        self,
        name: str,
        default: Any = _UNSET,
        *,
        required: bool = False,
        schemes: Optional[Iterable[str]] = ("http", "https"),
    ) -> str:
        """Return the variable as a validated URL string.

        Requires a scheme and a network location. Restrict the allowed scheme
        with ``schemes`` (default ``("http", "https")``); pass ``schemes=None``
        to allow any.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        text = raw.strip()
        parsed = urllib.parse.urlparse(text)
        if not parsed.scheme or not parsed.netloc:
            raise CastError(
                self._prefix + name, raw, "URL", hint="Expected e.g. 'https://host/path'."
            )
        if schemes is not None and parsed.scheme not in set(schemes):
            allowed = ", ".join(schemes)
            raise ValidationError(
                self._prefix + name, text, f"URL scheme must be one of: {allowed}"
            )
        return text

    def secret(self, name: str, default: Any = _UNSET, *, required: bool = False) -> Secret:
        """Return the variable wrapped in a :class:`Secret` that masks itself.

        The value never appears in logs, reprs, or tracebacks; call
        ``.reveal()`` at the point of use. A ``default`` (e.g. ``None``) is
        returned unchanged — wrap it in ``Secret`` yourself if you need masking.
        """
        raw = self._raw(name, default, required)
        if raw is _USE_DEFAULT:
            return default
        return Secret(raw)

    # -- scoping -----------------------------------------------------------

    def prefixed(self, prefix: str) -> "Env":
        """Return a new :class:`Env` with ``prefix`` appended to this one's.

        Chainable, so ``Env(prefix="APP_").prefixed("DB_").str("HOST")`` reads
        ``APP_DB_HOST`` from the same source.
        """
        return Env(source=self._source, prefix=self._prefix + prefix)

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


# Every typed getter on Env — collect() wraps each so it records errors
# instead of raising. Listed explicitly so unrelated methods aren't proxied.
_GETTERS = frozenset(
    {
        "str", "int", "float", "bool", "list", "json", "path", "cast",
        "decimal", "duration", "datetime", "date", "bytes", "url", "secret",
    }
)


class _Collector:
    """Wraps an :class:`Env` so failing getters record their error instead of
    raising (see :meth:`Env.collect`). Any getter on ``Env`` is proxied."""

    def __init__(self, parent: Env) -> None:
        self._parent = parent
        self.errors: List[EnvError] = []

    def __getattr__(self, attr: str) -> Any:
        if attr not in _GETTERS:
            raise AttributeError(attr)
        target = getattr(self._parent, attr)

        def guarded(*args: Any, **kwargs: Any) -> Any:
            try:
                return target(*args, **kwargs)
            except EnvError as exc:
                self.errors.append(exc)
                return None

        return guarded


# A ready-to-use instance bound to the live process environment.
env = Env()
