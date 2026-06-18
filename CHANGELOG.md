# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

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
