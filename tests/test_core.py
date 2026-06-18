import json

import pytest

from envcast import CastError, Env, MissingEnvError


def make(**values):
    return Env(source=dict(values))


# -- str ------------------------------------------------------------------


def test_str_present_and_default():
    e = make(NAME="alice")
    assert e.str("NAME") == "alice"
    assert e.str("MISSING", default="fallback") == "fallback"


def test_empty_string_is_a_value_not_missing():
    e = make(NAME="")
    assert e.str("NAME") == ""


# -- int / float ----------------------------------------------------------


def test_int_parses_and_strips_whitespace():
    assert make(PORT="  8000 ").int("PORT") == 8000


def test_int_bad_value_raises_casterror_with_name():
    with pytest.raises(CastError) as exc:
        make(PORT="abc").int("PORT")
    assert exc.value.name == "PORT"


def test_float_parses():
    assert make(RATE="1.5").float("RATE") == 1.5


# -- bool -----------------------------------------------------------------


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "t", "yes", "Y", "on"])
def test_bool_truthy(raw):
    assert make(FLAG=raw).bool("FLAG") is True


@pytest.mark.parametrize("raw", ["0", "false", "F", "no", "n", "OFF"])
def test_bool_falsy(raw):
    assert make(FLAG=raw).bool("FLAG") is False


def test_bool_invalid_raises():
    with pytest.raises(CastError):
        make(FLAG="maybe").bool("FLAG")


def test_bool_default():
    assert make().bool("FLAG", default=False) is False


# -- list -----------------------------------------------------------------


def test_list_splits_strips_and_drops_empty():
    e = make(HOSTS="a, b ,, c")
    assert e.list("HOSTS") == ["a", "b", "c"]


def test_list_custom_sep_and_cast():
    e = make(NUMS="1|2|3")
    assert e.list("NUMS", sep="|", cast=int) == [1, 2, 3]


def test_list_cast_failure_raises():
    with pytest.raises(CastError):
        make(NUMS="1,x,3").list("NUMS", cast=int)


def test_list_default():
    assert make().list("HOSTS", default=[]) == []


# -- json -----------------------------------------------------------------


def test_json_parses_object():
    e = make(CONF=json.dumps({"a": 1, "b": [2, 3]}))
    assert e.json("CONF") == {"a": 1, "b": [2, 3]}


def test_json_invalid_raises():
    with pytest.raises(CastError):
        make(CONF="{not json}").json("CONF")


# -- path -----------------------------------------------------------------


def test_path_returns_pathlib():
    from pathlib import Path

    assert make(DIR="/tmp/x").path("DIR") == Path("/tmp/x")


# -- cast -----------------------------------------------------------------


def test_custom_cast():
    e = make(COLOR="ff0000")
    assert e.cast("COLOR", lambda v: int(v, 16)) == 0xFF0000


def test_custom_cast_wraps_errors():
    with pytest.raises(CastError):
        make(COLOR="zzz").cast("COLOR", lambda v: int(v, 16))


# -- required / missing ---------------------------------------------------


def test_missing_without_default_raises():
    with pytest.raises(MissingEnvError):
        make().str("SECRET")


def test_required_true_raises_even_with_default():
    with pytest.raises(MissingEnvError):
        make().str("SECRET", default="x", required=True)


def test_missing_error_is_keyerror_subclass():
    assert issubclass(MissingEnvError, KeyError)


# -- prefix & live os.environ --------------------------------------------


def test_prefix():
    e = Env(source={"APP_PORT": "9000"}, prefix="APP_")
    assert e.int("PORT") == 9000


def test_default_env_reads_live_os_environ(monkeypatch):
    from envcast import env

    monkeypatch.setenv("ENVCAST_TEST_X", "42")
    assert env.int("ENVCAST_TEST_X") == 42
