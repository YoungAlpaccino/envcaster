from envcast import load_dotenv, read_dotenv

SAMPLE = """\
# a comment
NAME=alice
export TOKEN=secret
QUOTED="hello world"
SINGLE='single quoted'
WITH_COMMENT=value   # trailing comment
EMPTY=

  # indented comment
PORT=8000
"""


def write(tmp_path, text=SAMPLE):
    f = tmp_path / ".env"
    f.write_text(text, encoding="utf-8")
    return f


def test_read_dotenv_parses_all_forms(tmp_path):
    data = read_dotenv(write(tmp_path))
    assert data["NAME"] == "alice"
    assert data["TOKEN"] == "secret"          # export prefix stripped
    assert data["QUOTED"] == "hello world"    # double quotes stripped
    assert data["SINGLE"] == "single quoted"  # single quotes stripped
    assert data["WITH_COMMENT"] == "value"    # inline comment dropped
    assert data["EMPTY"] == ""
    assert data["PORT"] == "8000"


def test_read_dotenv_missing_file_returns_empty(tmp_path):
    assert read_dotenv(tmp_path / "nope.env") == {}


def test_quoted_value_keeps_hash(tmp_path):
    f = write(tmp_path, 'URL="http://x/#frag"\n')
    assert read_dotenv(f)["URL"] == "http://x/#frag"


def test_load_dotenv_does_not_override_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("NAME", "real")
    load_dotenv(write(tmp_path))
    import os

    assert os.environ["NAME"] == "real"        # existing env wins
    assert os.environ["TOKEN"] == "secret"     # new key injected


def test_load_dotenv_override(tmp_path, monkeypatch):
    monkeypatch.setenv("NAME", "real")
    load_dotenv(write(tmp_path), override=True)
    import os

    assert os.environ["NAME"] == "alice"
