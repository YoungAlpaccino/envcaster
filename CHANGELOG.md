# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

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
