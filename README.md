# envcaster ⚙️

> Read environment variables as the **type you actually want** — `int`, `bool`, `list`, `json`, `Path` — with defaults, required-checks, and errors that name the offending variable. Zero dependencies, pure standard library.

[![CI](https://github.com/YoungAlpaccino/envcast/actions/workflows/ci.yml/badge.svg)](https://github.com/YoungAlpaccino/envcast/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/envcaster.svg)](https://pypi.org/project/envcaster/)
[![Python](https://img.shields.io/pypi/pyversions/envcaster.svg)](https://pypi.org/project/envcaster/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`os.environ` only ever gives you strings. So every project grows the same little
pile of `int(os.environ.get("PORT", "8000"))` and hand-rolled truthy checks that
quietly treat `"False"` as `True`. **envcaster** is that pile, done once and done right.

- 🪶 **Zero required dependencies** — pure standard library.
- 🎯 **Typed getters** — `str · int · float · bool · list · json · path · decimal · duration · datetime · date · bytes · url` (+ custom `cast`).
- ✅ **Built-in validation** — `choices`, `min`/`max` bounds, and a `ValidationError` that's distinct from parse failures.
- 📋 **Batch config checks** — `env.collect()` reports *every* bad/missing variable at once, not one per restart.
- 🧯 **Loud, precise errors** — missing or malformed values tell you *which* variable and *why*.
- 🧪 **Fully tested** across Python 3.9–3.12.
- 🧩 **Drop-in `.env` loader** with optional `${VAR}` interpolation — never clobbers real environment config.

---

## Install

```bash
pip install envcaster
```

---

## Quick start

```python
from envcaster import env

PORT    = env.int("PORT", default=8000)
DEBUG   = env.bool("DEBUG", default=False)
HOSTS   = env.list("ALLOWED_HOSTS", sep=",")          # ["a", "b"] from "a,b"
TIMEOUT = env.float("TIMEOUT", default=1.5)
SECRET  = env.str("SECRET_KEY", required=True)         # raises if not set
DATA    = env.path("DATA_DIR", default="/var/data")   # -> pathlib.Path
FLAGS   = env.json("FEATURE_FLAGS", default={})        # parsed JSON
```

> **A variable is required unless you give it a `default`.** Missing required
> variables raise `MissingEnvError`; bad values raise `CastError`. Both subclass
> `EnvError` — catch broadly or narrowly.

---

## Usage

### Booleans that actually behave

```python
env.bool("DEBUG")     # 1 true t yes y on  -> True   (case-insensitive)
                      # 0 false f no n off -> False
                      # anything else      -> CastError
```

No more `bool("False") == True` bugs.

### Lists (and lists of other types)

```python
env.list("ALLOWED_HOSTS")                 # "a, b ,, c" -> ["a", "b", "c"]  (trims, drops empties)
env.list("PORTS", sep=":", cast=int)      # "80:443"    -> [80, 443]
env.list("TAGS", default=[])              # missing     -> []
```

### JSON and paths

```python
env.json("LIMITS")          # '{"rpm": 60}' -> {"rpm": 60}
env.path("LOG_DIR")         # "/var/log"    -> PosixPath("/var/log")
```

### Richer types — money, durations, dates, bytes, URLs

```python
from decimal import Decimal

env.decimal("PRICE")                       # "9.99"      -> Decimal("9.99")  (exact)
env.duration("TIMEOUT")                    # "1h30m"     -> timedelta(seconds=5400)
env.duration("RETRY", default=None)        # "500ms"     -> timedelta(microseconds=500000)
env.datetime("STARTS_AT")                  # "2026-06-22T12:00:00Z" -> aware datetime (UTC)
env.date("RELEASE_DAY")                    # "2026-06-22" -> date(2026, 6, 22)
env.bytes("API_KEY", encoding="base64")    # "aGVsbG8="  -> b"hello"
env.url("WEBHOOK_URL")                     # requires scheme+host; http/https by default
env.url("REDIS_URL", schemes=["redis"])    # restrict allowed schemes
```

`duration` accepts plain seconds or `ms s m h d w` tokens (`"30"`, `"5m"`,
`"1h30m"`, `"2d"`). `decimal`/`duration`/`datetime`/`date` all take `min`/`max`.

### Anything else — bring your own cast

```python
from decimal import Decimal

env.cast("PRICE", Decimal)                 # "9.99" -> Decimal("9.99")
env.cast("COLOR", lambda v: int(v, 16))    # "ff0000" -> 16711680
# exceptions from your function are wrapped in CastError, naming the variable
```

### Validate values — `choices`, `min`, `max`

```python
env.str("STAGE", choices=["dev", "staging", "prod"])   # else ValidationError
env.int("PORT", min=1, max=65535)                       # range-checked
env.float("SAMPLE_RATE", min=0.0, max=1.0)
env.cast("LEVEL", str.upper, choices=["INFO", "DEBUG"]) # choices check the converted value
```

A value that parses but breaks a constraint raises `ValidationError` (a
`ValueError`), kept distinct from `CastError` (which means it couldn't be parsed
at all). A `default` you supply is trusted and never constraint-checked.

### Validate a whole config at once — `collect()`

Stop debugging your config one missing variable per restart. `collect()` gathers
**every** error in the block and raises a single report:

```python
from envcaster import env

with env.collect() as cfg:
    PORT   = cfg.int("PORT", default=8000)
    SECRET = cfg.str("SECRET_KEY", required=True)
    DB_URL = cfg.str("DATABASE_URL", required=True)
    REGION = cfg.str("REGION", choices=["us", "eu"])

# If SECRET_KEY and DATABASE_URL are both missing, you get ONE error:
#   EnvValidationError: 2 environment variable errors found:
#     - Required environment variable 'SECRET_KEY' is not set.
#     - Required environment variable 'DATABASE_URL' is not set.
```

### Scoped readers with a prefix

```python
from envcaster import Env

app = Env(prefix="APP_")
app.int("PORT")        # reads APP_PORT
app.bool("DEBUG")      # reads APP_DEBUG

db = app.prefixed("DB_")   # chain prefixes
db.str("HOST")             # reads APP_DB_HOST
```

### Read from somewhere other than `os.environ`

```python
cfg = Env(source={"PORT": "9000"})   # great for tests — no global state
cfg.int("PORT")                       # 9000
```

### Load a `.env` file (no dependency)

```python
from envcaster import load_dotenv, env

load_dotenv()                  # reads ./.env into os.environ (won't override real env vars)
load_dotenv(".env.local", override=True)

PORT = env.int("PORT")

# Or parse without touching the environment:
from envcaster import read_dotenv
values = read_dotenv(".env")   # -> {"PORT": "8000", ...}

# Opt in to ${VAR} / $VAR expansion (from earlier keys, then os.environ):
read_dotenv(".env", interpolate=True)        # HOST=localhost / URL=http://${HOST} -> http://localhost
```

Handles `KEY=value`, `export KEY=value`, `# comments`, and quoted values.
Single-quoted values stay literal and `\$` is an escaped dollar. For multiline
values, use [python-dotenv](https://github.com/theskumar/python-dotenv).

---

## API reference

| Call | Returns | Notes |
|---|---|---|
| `env.str(name, default=…, required=False, choices=None)` | `str` | The raw value, unchanged |
| `env.int(name, …, min=None, max=None, choices=None)` | `int` | Base-10, whitespace stripped |
| `env.float(name, …, min=None, max=None, choices=None)` | `float` | |
| `env.bool(name, …)` | `bool` | `1/true/t/yes/y/on` ↔ `0/false/f/no/n/off` |
| `env.list(name, …, sep=",", cast=str)` | `list` | Trims items, drops empties, per-item `cast` |
| `env.json(name, …)` | `Any` | `json.loads` of the value |
| `env.path(name, …)` | `pathlib.Path` | Not resolved/validated |
| `env.decimal(name, …, min=None, max=None, choices=None)` | `Decimal` | Exact precision |
| `env.duration(name, …, min=None, max=None)` | `timedelta` | Seconds or `500ms`/`5m`/`1h30m`/`2d`/`1w` |
| `env.datetime(name, …, min=None, max=None)` | `datetime` | ISO 8601; trailing `Z` = UTC |
| `env.date(name, …, min=None, max=None)` | `date` | ISO 8601 `YYYY-MM-DD` |
| `env.bytes(name, …, encoding="utf-8")` | `bytes` | Codec, or `base64`/`hex` |
| `env.url(name, …, schemes=("http","https"))` | `str` | Validated; requires scheme + host |
| `env.cast(name, func, …, choices=None)` | `Any` | Apply any callable; errors wrapped in `CastError` |
| `env.collect()` | context manager | Batch-validate; raises one `EnvValidationError` |
| `env.prefixed(prefix)` | `Env` | New reader with a combined prefix |
| `Env(source=None, prefix="")` | `Env` | Custom mapping and/or name prefix |
| `read_dotenv(path=".env", interpolate=False)` | `dict` | Parse a `.env` file; `{}` if absent |
| `load_dotenv(path=".env", override=False, interpolate=False)` | `dict` | Inject into `os.environ` |

**Errors:** `EnvError` (base) · `MissingEnvError` (also `KeyError`) · `CastError` (also `ValueError`) · `ValidationError` (also `ValueError`, for `choices`/`min`/`max`) · `EnvValidationError` (aggregate from `collect()`).

---

## Why not just `os.environ`?

```python
# Before
import os
PORT  = int(os.environ.get("PORT", "8000"))
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")
HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]

# After
from envcaster import env
PORT  = env.int("PORT", default=8000)
DEBUG = env.bool("DEBUG", default=False)
HOSTS = env.list("ALLOWED_HOSTS", default=[])
```

---

## Development

```bash
git clone https://github.com/YoungAlpaccino/envcast
cd envcast
pip install -e ".[dev]"
pytest          # run tests
ruff check .    # lint
```

---

## License

MIT — see [LICENSE](./LICENSE). Use it anywhere, including commercially.
