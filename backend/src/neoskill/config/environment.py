"""Validate deployment input without coupling domain modules to environment variables."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class DatabaseEnvironment:
    name: str
    user: str
    password: str
    host: str
    port: int


@dataclass(frozen=True)
class EmailEnvironment:
    host: str
    port: int
    user: str
    password: str
    use_tls: bool
    from_address: str


@dataclass(frozen=True)
class Environment:
    mode: str
    debug: bool
    secret_key: str
    allowed_hosts: tuple[str, ...]
    cors_origins: tuple[str, ...]
    ssl_redirect: bool
    database: DatabaseEnvironment | None
    email: EmailEnvironment | None
    frontend_url: str
    media_root: str


def _boolean(values: Mapping[str, str], name: str) -> bool:
    value = values.get(name, "false").strip().lower()
    if value not in {"true", "false"}:
        raise ImproperlyConfigured(f"{name} must be true or false.")
    return value == "true"


def _items(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


def _database(values: Mapping[str, str], mode: str) -> DatabaseEnvironment | None:
    names = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_HOST", "POSTGRES_PORT")
    provided = {name: values.get(name, "").strip() for name in names}
    if not any(provided.values()):
        return None
    if missing := [name for name, value in provided.items() if not value]:
        raise ImproperlyConfigured(f"PostgreSQL configuration is incomplete: {', '.join(missing)}.")

    for name in ("POSTGRES_DB", "POSTGRES_USER"):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", provided[name]):
            raise ImproperlyConfigured(f"{name} must be a safe PostgreSQL identifier.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*|[0-9a-fA-F:]+", provided["POSTGRES_HOST"]):
        raise ImproperlyConfigured(
            "POSTGRES_HOST must be a hostname or IP address without a scheme."
        )
    try:
        port = int(provided["POSTGRES_PORT"])
    except ValueError as error:
        raise ImproperlyConfigured(
            "POSTGRES_PORT must be an integer between 1 and 65535."
        ) from error
    if not 1 <= port <= 65535:
        raise ImproperlyConfigured("POSTGRES_PORT must be an integer between 1 and 65535.")

    password = provided["POSTGRES_PASSWORD"]
    if len(password) < 16:
        raise ImproperlyConfigured("POSTGRES_PASSWORD must contain at least 16 characters.")
    if mode == "production" and password.startswith(("dev-", "test-")):
        raise ImproperlyConfigured("Replace the development POSTGRES_PASSWORD in production.")

    return DatabaseEnvironment(
        name=provided["POSTGRES_DB"],
        user=provided["POSTGRES_USER"],
        password=password,
        host=provided["POSTGRES_HOST"],
        port=port,
    )


def _email(values: Mapping[str, str]) -> EmailEnvironment | None:
    """SMTP is optional: without it Django writes reset mail to the console."""
    names = ("EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "EMAIL_FROM")
    provided = {name: values.get(name, "").strip() for name in names}
    if not any(provided.values()):
        return None
    if missing := [name for name, value in provided.items() if not value]:
        raise ImproperlyConfigured(f"Email configuration is incomplete: {', '.join(missing)}.")
    try:
        port = int(provided["EMAIL_PORT"])
    except ValueError:
        raise ImproperlyConfigured("EMAIL_PORT must be a number.") from None
    if not 1 <= port <= 65535:
        raise ImproperlyConfigured("EMAIL_PORT must be between 1 and 65535.")
    if "@" not in provided["EMAIL_FROM"]:
        raise ImproperlyConfigured("EMAIL_FROM must be an email address.")
    return EmailEnvironment(
        host=provided["EMAIL_HOST"],
        port=port,
        user=provided["EMAIL_HOST_USER"],
        password=provided["EMAIL_HOST_PASSWORD"],
        use_tls=values.get("EMAIL_USE_TLS", "true").strip().lower() != "false",
        from_address=provided["EMAIL_FROM"],
    )


def _media_root(values: Mapping[str, str]) -> str:
    """Uploaded images live here; the deployment must mount it as a durable volume."""
    raw = values.get("MEDIA_ROOT", "").strip()
    return raw or "/tmp/neoskill-media"


def _frontend_url(values: Mapping[str, str]) -> str:
    """Password reset links point back at the web app, so the origin must be explicit."""
    raw = values.get("FRONTEND_URL", "http://localhost:3000").strip().rstrip("/")
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ImproperlyConfigured("FRONTEND_URL must be an absolute http(s) URL.")
    return raw


def load_environment(values: Mapping[str, str]) -> Environment:
    mode = values.get("APP_ENV", "production")
    if mode not in {"local", "test", "production"}:
        raise ImproperlyConfigured("APP_ENV must be local, test or production.")

    debug = _boolean(values, "DJANGO_DEBUG")
    if mode == "production" and debug:
        raise ImproperlyConfigured("DJANGO_DEBUG must be false in production.")

    secret = values.get("DJANGO_SECRET_KEY", "")
    if len(secret) < 50 or len(set(secret)) < 5:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be a strong key of at least 50 characters."
        )
    if mode == "production" and secret.startswith(("dev-", "test-", "django-insecure-")):
        raise ImproperlyConfigured("Replace the development DJANGO_SECRET_KEY in production.")

    hosts = _items(values.get("DJANGO_ALLOWED_HOSTS", ""))
    if not hosts or any(
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*|\[[0-9a-fA-F:]+\]", host) for host in hosts
    ):
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list explicit hosts without ports.")

    origins = _items(values.get("CORS_ALLOWED_ORIGINS", ""))
    for origin in origins:
        try:
            parsed = urlsplit(origin)
            port = parsed.port  # Validate malformed/out-of-range ports as well.
            valid = (
                parsed.scheme in {"http", "https"}
                and parsed.hostname is not None
                and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*|[0-9a-fA-F:]+", parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and not parsed.path
                and not parsed.query
                and not parsed.fragment
                and (port is None or port > 0)
            )
        except ValueError:
            valid = False
        if not valid or (mode == "production" and parsed.scheme != "https"):
            raise ImproperlyConfigured(
                "CORS_ALLOWED_ORIGINS must contain exact origins; use HTTPS in production."
            )

    return Environment(
        mode=mode,
        debug=debug,
        secret_key=secret,
        allowed_hosts=hosts,
        cors_origins=origins,
        ssl_redirect=_boolean(values, "DJANGO_SSL_REDIRECT"),
        database=_database(values, mode),
        email=_email(values),
        frontend_url=_frontend_url(values),
        media_root=_media_root(values),
    )
