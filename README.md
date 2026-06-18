# envcast ⚙️

> Read environment variables as the **type you actually want** — `int`, `bool`, `list`, `json`, `Path` — with defaults, required-checks, and errors that name the offending variable. Zero dependencies, pure standard library.

[![CI](https://github.com/YoungAlpaccino/envcast/actions/workflows/ci.yml/badge.svg)](https://github.com/YoungAlpaccino/envcast/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/envcast.svg)](https://pypi.org/project/envcast/)
[![Python](https://img.shields.io/pypi/pyversions/envcast.svg)](https://pypi.org/project/envcast/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`os.environ` only ever gives you strings. So every project grows the same little
pile of `int(os.environ.get("PORT", "8000"))` and hand-rolled truthy checks that
quietly treat `"False"` as `True`. **envcast** is that pile, done once and done right.

- 🪶 **Zero required dependencies** — pure standard library.
- 🎯 **Typed getters** — `str · int · float · bool · list · json · path` (+ custom `cast`).
- 🧯 **Loud, precise errors** — missing or malformed values tell you *which* variable and *why*.
- 🧪 **Fully tested** across Python 3.9–3.12.
- 🧩 **Drop-in `.env` loader** that never clobbers real environment config.

---

## Install

```bash
pip install envcast
```

---

## Quick start

```python
from envcast import env

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

### Anything else — bring your own cast

```python
from decimal import Decimal

env.cast("PRICE", Decimal)                 # "9.99" -> Decimal("9.99")
env.cast("COLOR", lambda v: int(v, 16))    # "ff0000" -> 16711680
# exceptions from your function are wrapped in CastError, naming the variable
```

### Scoped readers with a prefix

```python
from envcast import Env

app = Env(prefix="APP_")
app.int("PORT")        # reads APP_PORT
app.bool("DEBUG")      # reads APP_DEBUG
```

### Read from somewhere other than `os.environ`

```python
cfg = Env(source={"PORT": "9000"})   # great for tests — no global state
cfg.int("PORT")                       # 9000
```

### Load a `.env` file (no dependency)

```python
from envcast import load_dotenv, env

load_dotenv()                  # reads ./.env into os.environ (won't override real env vars)
load_dotenv(".env.local", override=True)

PORT = env.int("PORT")

# Or parse without touching the environment:
from envcast import read_dotenv
values = read_dotenv(".env")   # -> {"PORT": "8000", ...}
```

Handles `KEY=value`, `export KEY=value`, `# comments`, and quoted values. For
interpolation or multiline values, use [python-dotenv](https://github.com/theskumar/python-dotenv).

---

## API reference

| Call | Returns | Notes |
|---|---|---|
| `env.str(name, default=…, required=False)` | `str` | The raw value, unchanged |
| `env.int(name, …)` | `int` | Base-10, whitespace stripped |
| `env.float(name, …)` | `float` | |
| `env.bool(name, …)` | `bool` | `1/true/t/yes/y/on` ↔ `0/false/f/no/n/off` |
| `env.list(name, …, sep=",", cast=str)` | `list` | Trims items, drops empties, per-item `cast` |
| `env.json(name, …)` | `Any` | `json.loads` of the value |
| `env.path(name, …)` | `pathlib.Path` | Not resolved/validated |
| `env.cast(name, func, …)` | `Any` | Apply any callable; errors wrapped in `CastError` |
| `Env(source=None, prefix="")` | `Env` | Custom mapping and/or name prefix |
| `read_dotenv(path=".env")` | `dict` | Parse a `.env` file; `{}` if absent |
| `load_dotenv(path=".env", override=False)` | `dict` | Inject into `os.environ` |

**Errors:** `EnvError` (base) · `MissingEnvError` (also `KeyError`) · `CastError` (also `ValueError`).

---

## Why not just `os.environ`?

```python
# Before
import os
PORT  = int(os.environ.get("PORT", "8000"))
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")
HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "").split(",") if h.strip()]

# After
from envcast import env
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
