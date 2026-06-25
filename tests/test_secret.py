"""Tests for the Secret wrapper added in 0.4.0."""

from envcaster import Env, Secret


def make(**values):
    return Env(source=dict(values))


def test_secret_masks_str_and_repr():
    s = make(TOKEN="hunter2").secret("TOKEN")
    assert str(s) == "***"
    assert repr(s) == "Secret('***')"
    assert f"{s}" == "***"
    assert "hunter2" not in f"value is {s!r} / {s}"


def test_secret_reveals_real_value():
    s = make(TOKEN="hunter2").secret("TOKEN")
    assert s.reveal() == "hunter2"


def test_secret_equality_without_reveal():
    s = make(TOKEN="hunter2").secret("TOKEN")
    assert s == "hunter2"
    assert s == Secret("hunter2")
    assert s != Secret("other")


def test_secret_bool_and_len():
    assert bool(make(T="x").secret("T")) is True
    assert bool(Secret("")) is False
    assert len(make(T="abc").secret("T")) == 3


def test_secret_default_returned_unchanged():
    assert make().secret("MISSING", default=None) is None


def test_secret_is_immutable():
    s = Secret("x")
    try:
        s._value = "y"  # type: ignore[misc]
    except AttributeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Secret should be immutable")
    assert s.reveal() == "x"


def test_secret_in_collect():
    from envcaster import EnvValidationError

    e = make()
    try:
        with e.collect() as cfg:
            cfg.secret("API_KEY", required=True)
    except EnvValidationError as exc:
        assert "API_KEY" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected EnvValidationError")
