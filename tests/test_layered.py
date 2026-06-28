"""Tests for multi-file discovery and layering added in 0.5.0."""

import os

from envcaster import find_dotenv, load_layered, load_stack


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_find_dotenv_walks_up(tmp_path):
    write(tmp_path / ".env", "X=1")
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    found = find_dotenv(start=deep)
    assert found == str((tmp_path / ".env").resolve())


def test_find_dotenv_missing_returns_empty(tmp_path):
    assert find_dotenv(start=tmp_path) == ""


def test_load_layered_later_wins(tmp_path, monkeypatch):
    monkeypatch.delenv("SHARED", raising=False)
    monkeypatch.delenv("ONLY_BASE", raising=False)
    write(tmp_path / ".env", "SHARED=base\nONLY_BASE=b")
    write(tmp_path / ".env.local", "SHARED=local")
    merged = load_layered([tmp_path / ".env", tmp_path / ".env.local"])
    assert merged["SHARED"] == "local"      # later file wins
    assert merged["ONLY_BASE"] == "b"
    assert os.environ["SHARED"] == "local"


def test_load_layered_real_env_wins_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("SHARED", "real")
    write(tmp_path / ".env", "SHARED=file")
    load_layered([tmp_path / ".env"])
    assert os.environ["SHARED"] == "real"


def test_load_layered_override_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SHARED", "real")
    write(tmp_path / ".env", "SHARED=file")
    load_layered([tmp_path / ".env"], override_env=True)
    assert os.environ["SHARED"] == "file"


def test_load_stack_precedence(tmp_path, monkeypatch):
    for k in ("A", "B", "C"):
        monkeypatch.delenv(k, raising=False)
    write(tmp_path / ".env", "A=base\nB=base\nC=base")
    write(tmp_path / ".env.prod", "B=prod")
    write(tmp_path / ".env.local", "C=local")
    merged = load_stack("prod", root=tmp_path)
    assert merged["A"] == "base"
    assert merged["B"] == "prod"    # stage file beats base
    assert merged["C"] == "local"   # .local beats base


def test_load_stack_skips_missing_files(tmp_path, monkeypatch):
    monkeypatch.delenv("ONLY", raising=False)
    write(tmp_path / ".env", "ONLY=here")
    merged = load_stack("nope", root=tmp_path)  # stage files absent
    assert merged == {"ONLY": "here"}
