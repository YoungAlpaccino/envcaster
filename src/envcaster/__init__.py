"""envcaster — typed, dependency-free environment variable loading.

Read environment variables as the type you actually want — ``int``, ``float``,
``bool``, ``list``, ``json``, ``Path`` — with defaults, required-checks, and
error messages that tell you exactly which variable was wrong and why. Plus a
tiny ``.env`` loader. Zero dependencies, pure standard library.

    from envcaster import env

    PORT = env.int("PORT", default=8000)
    DEBUG = env.bool("DEBUG", default=False)
    HOSTS = env.list("ALLOWED_HOSTS", sep=",")
    SECRET = env.str("SECRET_KEY", required=True)
"""

from envcaster.core import (
    CastError,
    Env,
    EnvError,
    EnvValidationError,
    MissingEnvError,
    Secret,
    ValidationError,
    env,
)
from envcaster.dotenv import (
    find_dotenv,
    load_dotenv,
    load_layered,
    load_stack,
    read_dotenv,
)

__version__ = "0.5.0"

__all__ = [
    "env",
    "Env",
    "Secret",
    "EnvError",
    "MissingEnvError",
    "CastError",
    "ValidationError",
    "EnvValidationError",
    "load_dotenv",
    "read_dotenv",
    "find_dotenv",
    "load_layered",
    "load_stack",
]
