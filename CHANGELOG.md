# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.6.0] - 2026-06-22

### Added
- Audit trail — every `Env` now records which variables it reads:
  - `env.used()` / `env.missing()` — names that were present / looked up but absent.
  - `env.unused()` — source variables (under the prefix) never read; spots dead
    or misspelled config.
  - `env.dump(mask_secrets=True)` — `{name: value}` of everything read, masking
    values read via `secret()` or whose name looks sensitive (`*TOKEN*`,
    `*PASSWORD*`, …). Safe to log.
  - `env.reset_audit()` — clear the record.

### Notes
- Fully backward compatible.

## [0.5.0] - 2026-06-22

### Added
- `find_dotenv()` — search upward from a directory to the filesystem root for a
  `.env`, so the project file is found from any subdirectory.
- `load_layered(paths, …)` — load several `.env` files in order, later files
  overriding earlier ones; real environment still wins unless `override_env=True`.
- `load_stack(stage, …)` — load the conventional cascade
  `.env < .env.<stage> < .env.local < .env.<stage>.local`.

### Notes
- Fully backward compatible.

## [0.4.0] - 2026-06-22

### Added
- `Secret` — a wrapper that masks its value in `str()`, `repr()`, `format()`,
  f-strings, and tracebacks, so secrets never leak into logs by accident. Call
  `.reveal()` at the point of use. Supports `==`, `bool()`, and `len()` without
  revealing, and is immutable.
- `env.secret(name, …)` — read a variable as a `Secret`. Covered by `collect()`.

### Notes
- Fully backward compatible.

## [0.3.0] - 2026-06-22

### Added
- New typed getters:
  - `decimal` — exact `decimal.Decimal` (with `min`/`max`/`choices`).
  - `duration` — `datetime.timedelta` from seconds or `500ms` / `5m` / `1h30m` /
    `2d` / `1w` forms (with `min`/`max`).
  - `datetime` / `date` — ISO 8601 parsing; a trailing `Z` is treated as UTC
    (with `min`/`max`).
  - `bytes` — `utf-8` (or any codec) by default, plus `encoding="base64"` /
    `encoding="hex"` decoders for keys and secrets.
  - `url` — a validated URL string; requires scheme + host and restricts the
    scheme via `schemes=` (default `http`/`https`, `None` to allow any).
- `Env.prefixed(prefix)` — derive a new reader with a combined prefix, e.g.
  `Env(prefix="APP_").prefixed("DB_").str("HOST")` reads `APP_DB_HOST`.
- `collect()` now auto-covers every getter (including all of the above); adding a
  getter no longer requires updating the batch-validation wrapper.

### Notes
- Fully backward compatible — all additions are new getters/options.

## [0.2.0] - 2026-06-19

### Added
- `choices=` on `str`, `int`, `float`, and `cast` — restrict a value to an
  allowed set.
- `min=` / `max=` bounds on `int` and `float`.
- `ValidationError` — raised when a value parses but fails a `choices`/`min`/
  `max` constraint. Subclasses `EnvError` and `ValueError`, and is distinct from
  `CastError` (which means the value could not be parsed at all).
- `Env.collect()` — a context manager that validates a whole config block and
  raises a single `EnvValidationError` listing **every** problem at once, instead
  of failing on the first.
- `EnvValidationError` — aggregates the errors gathered by `collect()`.
- `read_dotenv` / `load_dotenv` gained an opt-in `interpolate=True` that expands
  `${VAR}` / `$VAR` references (from earlier keys, then `os.environ`). Single-
  quoted values stay literal and `\$` is an escaped dollar sign.

### Notes
- Fully backward compatible — all additions are new, keyword-only options.

## [0.1.0] - 2026-06-18

### Added
- `env` — a ready-to-use reader bound to the live process environment.
- `Env` — configurable reader with `source` (any mapping) and `prefix` support.
- Typed getters: `str`, `int`, `float`, `bool`, `list`, `json`, `path`, and a
  generic `cast` for arbitrary conversions.
- `default=` and `required=True` on every getter; variables are required unless
  a default is given.
- Clear errors: `EnvError` base, `MissingEnvError` (also a `KeyError`), and
  `CastError` (also a `ValueError`), each naming the offending variable.
- `read_dotenv` / `load_dotenv` — a tiny, dependency-free `.env` reader that
  never clobbers real environment variables unless `override=True`.
- `py.typed` marker — ships type information.
- Tested across Python 3.9–3.12 with CI.
