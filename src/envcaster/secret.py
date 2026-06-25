"""A wrapper that keeps secret values out of logs, reprs, and tracebacks."""

from __future__ import annotations

from typing import Any

__all__ = ["Secret"]

_MASK = "***"


class Secret:
    """Holds a sensitive string and refuses to show it.

    ``str()``, ``repr()``, ``format()``, and f-strings all render ``***`` — so a
    secret can never leak into a log line or traceback by accident. Call
    :meth:`reveal` to get the real value at the point of use::

        token = env.secret("API_TOKEN")
        print(token)            # ***
        requests.get(url, headers={"Authorization": token.reveal()})
    """

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def reveal(self) -> str:
        """Return the real underlying value."""
        return self._value

    # -- masking -----------------------------------------------------------

    def __str__(self) -> str:
        return _MASK

    def __repr__(self) -> str:
        return f"Secret({_MASK!r})"

    def __format__(self, _spec: str) -> str:
        return _MASK

    # -- safe comparisons without revealing --------------------------------

    def __bool__(self) -> bool:
        return bool(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __eq__(self, other: Any) -> Any:
        if isinstance(other, Secret):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    # -- prevent accidental mutation / attribute leakage -------------------

    def __setattr__(self, *_: Any) -> None:  # pragma: no cover - guard
        raise AttributeError("Secret is immutable")
