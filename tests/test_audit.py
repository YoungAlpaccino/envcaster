"""Tests for the audit/introspection features added in 0.6.0."""

from envcaster import Env


def make(**values):
    return Env(source=dict(values))


def test_used_and_missing():
    e = make(A="1", B="2", C="3")
    e.int("A")
    e.str("B")
    e.str("NOPE", default="x")  # looked up, absent
    assert e.used() == ["A", "B"]
    assert e.missing() == ["NOPE"]


def test_unused_lists_untouched_source_keys():
    e = make(A="1", B="2", C="3")
    e.int("A")
    assert e.unused() == ["B", "C"]


def test_dump_returns_read_values():
    e = make(HOST="db", PORT="5432")
    e.str("HOST")
    e.int("PORT")
    assert e.dump(mask_secrets=False) == {"HOST": "db", "PORT": "5432"}


def test_dump_masks_secret_getter():
    e = make(API_CREDENTIAL="abc")
    e.secret("API_CREDENTIAL")
    assert e.dump()["API_CREDENTIAL"] == "***"


def test_dump_masks_by_name_heuristic():
    e = make(DB_PASSWORD="pw", AUTH_TOKEN="tk", PORT="80")
    e.str("DB_PASSWORD")
    e.str("AUTH_TOKEN")
    e.int("PORT")
    dumped = e.dump()
    assert dumped["DB_PASSWORD"] == "***"
    assert dumped["AUTH_TOKEN"] == "***"
    assert dumped["PORT"] == "80"


def test_dump_can_disable_masking():
    e = make(SECRET_KEY="s")
    e.str("SECRET_KEY")
    assert e.dump(mask_secrets=False)["SECRET_KEY"] == "s"


def test_reset_audit():
    e = make(A="1")
    e.int("A")
    e.reset_audit()
    assert e.used() == []
    assert e.dump() == {}


def test_audit_respects_prefix():
    e = Env(source={"APP_X": "1", "OTHER": "2"}, prefix="APP_")
    e.int("X")
    assert e.used() == ["APP_X"]
    assert e.unused() == []  # OTHER is outside the prefix
