import json

import pytest

from envcaster import (
    CastError,
    Env,
    EnvValidationError,
    MissingEnvError,
    ValidationError,
)


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
    from envcaster import env

    monkeypatch.setenv("ENVCAST_TEST_X", "42")
    assert env.int("ENVCAST_TEST_X") == 42


# -- choices --------------------------------------------------------------


def test_str_choices_accepts_allowed():
    assert make(STAGE="prod").str("STAGE", choices=["dev", "prod"]) == "prod"


def test_str_choices_rejects_other():
    with pytest.raises(ValidationError) as exc:
        make(STAGE="staging").str("STAGE", choices=["dev", "prod"])
    assert exc.value.name == "STAGE"


def test_int_choices():
    assert make(V="2").int("V", choices=[1, 2, 3]) == 2
    with pytest.raises(ValidationError):
        make(V="9").int("V", choices=[1, 2, 3])


def test_cast_choices_checks_converted_value():
    assert make(LEVEL="INFO").cast("LEVEL", str.upper, choices=["INFO", "DEBUG"]) == "INFO"
    with pytest.raises(ValidationError):
        make(LEVEL="trace").cast("LEVEL", str.upper, choices=["INFO", "DEBUG"])


def test_choices_not_applied_to_default():
    # A provided default is trusted and not validated against choices.
    assert make().str("STAGE", default="anything", choices=["dev"]) == "anything"


# -- min / max ------------------------------------------------------------


def test_int_min_max_ok():
    assert make(PORT="8000").int("PORT", min=1, max=65535) == 8000


def test_int_below_min_raises():
    with pytest.raises(ValidationError) as exc:
        make(PORT="0").int("PORT", min=1)
    assert "must be >=" in str(exc.value)


def test_int_above_max_raises():
    with pytest.raises(ValidationError):
        make(PORT="70000").int("PORT", max=65535)


def test_float_bounds():
    assert make(R="0.5").float("R", min=0.0, max=1.0) == 0.5
    with pytest.raises(ValidationError):
        make(R="1.5").float("R", min=0.0, max=1.0)


def test_validation_error_is_value_error():
    assert issubclass(ValidationError, ValueError)


# -- collect (batch validation) -------------------------------------------


def test_collect_passes_when_all_valid():
    e = make(PORT="8000", SECRET="x")
    with e.collect() as cfg:
        port = cfg.int("PORT")
        secret = cfg.str("SECRET", required=True)
    assert port == 8000
    assert secret == "x"


def test_collect_reports_all_errors_at_once():
    e = make(PORT="not-a-number")
    with pytest.raises(EnvValidationError) as exc:
        with e.collect() as cfg:
            cfg.int("PORT")  # CastError
            cfg.str("SECRET", required=True)  # MissingEnvError
            cfg.str("DB_URL", required=True)  # MissingEnvError
    assert len(exc.value.errors) == 3
    message = str(exc.value)
    assert "PORT" in message and "SECRET" in message and "DB_URL" in message


def test_collect_returns_none_for_failed_getter_inside_block():
    e = make()
    captured = {}
    with pytest.raises(EnvValidationError):
        with e.collect() as cfg:
            captured["v"] = cfg.str("MISSING", required=True)
    assert captured["v"] is None


def test_collect_does_not_raise_when_empty():
    e = make(NAME="ok")
    with e.collect() as cfg:
        assert cfg.str("NAME") == "ok"
