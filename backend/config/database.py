"""Build Django database settings from deployment environment variables."""

import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


_TRUE_VALUES = {"true", "1", "yes"}


def _postgres_from_url(database_url):
    try:
        parsed = urlsplit(database_url)
        if parsed.scheme not in {"postgres", "postgresql"}:
            raise ValueError
        name = unquote(parsed.path.lstrip("/"))
        host = parsed.hostname
        port = parsed.port or 5432
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        options = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not all((name, host, user, password)):
            raise ValueError
    except (TypeError, ValueError):
        raise ImproperlyConfigured(
            "DATABASE_URL must be a valid PostgreSQL connection URL."
        ) from None

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": name,
        "USER": user,
        "PASSWORD": password,
        "HOST": host,
        "PORT": str(port),
        "OPTIONS": options,
        "CONN_MAX_AGE": 0,
    }


def _postgres_from_fields(env):
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST")
    if any(not env.get(key) for key in required):
        raise ImproperlyConfigured(
            "PostgreSQL requires POSTGRES_DB, POSTGRES_USER, "
            "POSTGRES_PASSWORD, and POSTGRES_HOST."
        )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env["POSTGRES_DB"],
        "USER": env["POSTGRES_USER"],
        "PASSWORD": env["POSTGRES_PASSWORD"],
        "HOST": env["POSTGRES_HOST"],
        "PORT": env.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 0,
    }


def database_settings(env=None, base_dir=None):
    """Return a PostgreSQL configuration for deployments or SQLite locally."""
    env = os.environ if env is None else env
    base_dir = Path(base_dir or Path(__file__).resolve().parents[1])
    database_url = env.get("DATABASE_URL")
    if database_url:
        return {"default": _postgres_from_url(database_url)}

    is_production = (
        bool(env.get("VERCEL"))
        or env.get("DJANGO_ENV", "").lower() == "production"
        or env.get("DJANGO_DEBUG", "true").lower() in {"false", "0", "no"}
    )
    use_sqlite = env.get("USE_SQLITE", "").lower() in _TRUE_VALUES

    if env.get("POSTGRES_DB") and not (use_sqlite and not is_production):
        return {"default": _postgres_from_fields(env)}

    if is_production:
        raise ImproperlyConfigured(
            "A valid DATABASE_URL or complete PostgreSQL configuration is required "
            "in production."
        )

    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": base_dir / "db.sqlite3",
        }
    }
