"""Tests for the richer typed getters added in 0.3.0."""

import datetime as dt
from decimal import Decimal

import pytest

from envcaster import CastError, Env, EnvValidationError, ValidationError


def make(**values):
    return Env(source=dict(values))


# -- decimal --------------------------------------------------------------


def test_decimal_exact():
    assert make(PRICE="9.99").decimal("PRICE") == Decimal("9.99")


def test_decimal_invalid_raises():
    with pytest.raises(CastError):
        make(PRICE="abc").decimal("PRICE")


def test_decimal_bounds():
    assert make(P="5").decimal("P", min=Decimal("1"), max=Decimal("10")) == Decimal("5")
    with pytest.raises(ValidationError):
        make(P="20").decimal("P", max=Decimal("10"))


def test_decimal_default():
    assert make().decimal("P", default=Decimal("0")) == Decimal("0")


# -- duration -------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, seconds",
    [
        ("30", 30),
        ("1.5", 1.5),
        ("500ms", 0.5),
        ("5m", 300),
        ("1h", 3600),
        ("2d", 172800),
        ("1h30m", 5400),
        ("1w", 604800),
        ("1H30M", 5400),  # case-insensitive
    ],
)
def test_duration_parses(raw, seconds):
    assert make(T=raw).duration("T") == dt.timedelta(seconds=seconds)


@pytest.mark.parametrize("raw", ["", "abc", "5x", "1h30", "5m junk", "h"])
def test_duration_invalid_raises(raw):
    with pytest.raises(CastError):
        make(T=raw).duration("T")


def test_duration_bounds():
    with pytest.raises(ValidationError):
        make(T="10s").duration("T", min=dt.timedelta(seconds=30))


def test_duration_default():
    assert make().duration("T", default=dt.timedelta(0)) == dt.timedelta(0)


# -- datetime / date ------------------------------------------------------


def test_datetime_iso():
    assert make(WHEN="2026-06-22T12:30:00").datetime("WHEN") == dt.datetime(2026, 6, 22, 12, 30)


def test_datetime_trailing_z_is_utc():
    value = make(WHEN="2026-06-22T12:00:00Z").datetime("WHEN")
    assert value.utcoffset() == dt.timedelta(0)


def test_datetime_invalid_raises():
    with pytest.raises(CastError):
        make(WHEN="not-a-date").datetime("WHEN")


def test_date_iso():
    assert make(DAY="2026-06-22").date("DAY") == dt.date(2026, 6, 22)


def test_date_bounds():
    with pytest.raises(ValidationError):
        make(DAY="2020-01-01").date("DAY", min=dt.date(2026, 1, 1))


# -- bytes ----------------------------------------------------------------


def test_bytes_utf8_default():
    assert make(K="hi").bytes("K") == b"hi"


def test_bytes_base64():
    assert make(K="aGVsbG8=").bytes("K", encoding="base64") == b"hello"


def test_bytes_hex():
    assert make(K="68656c6c6f").bytes("K", encoding="hex") == b"hello"


def test_bytes_invalid_base64_raises():
    with pytest.raises(CastError):
        make(K="not base64!!").bytes("K", encoding="base64")


def test_bytes_default():
    assert make().bytes("K", default=b"") == b""


# -- url ------------------------------------------------------------------


def test_url_valid():
    assert make(U="https://example.com/x").url("U") == "https://example.com/x"


def test_url_strips_whitespace():
    assert make(U="  https://example.com  ").url("U") == "https://example.com"


def test_url_missing_scheme_raises():
    with pytest.raises(CastError):
        make(U="example.com/x").url("U")


def test_url_scheme_not_allowed_raises():
    with pytest.raises(ValidationError):
        make(U="ftp://example.com").url("U")  # default schemes are http/https


def test_url_custom_schemes():
    assert make(U="redis://localhost:6379").url("U", schemes=["redis"]) == "redis://localhost:6379"


def test_url_any_scheme_when_none():
    assert make(U="ftp://h/x").url("U", schemes=None) == "ftp://h/x"


# -- prefixed -------------------------------------------------------------


def test_prefixed_combines():
    e = Env(source={"APP_DB_HOST": "db"}, prefix="APP_")
    assert e.prefixed("DB_").str("HOST") == "db"


def test_prefixed_shares_source():
    e = Env(source={"X_Y": "z"})
    assert e.prefixed("X_").str("Y") == "z"


# -- collect() covers the new getters automatically -----------------------


def test_collect_includes_new_getters():
    e = make(PRICE="bad", WHEN="nope")
    with pytest.raises(EnvValidationError) as exc:
        with e.collect() as cfg:
            cfg.decimal("PRICE")
            cfg.datetime("WHEN")
            cfg.url("API_URL", required=True)
    assert len(exc.value.errors) == 3
