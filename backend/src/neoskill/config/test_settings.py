"""PostgreSQL-only settings loaded before pytest-django initializes Django."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DJANGO_SECRET_KEY",
    "test-only-neoskill-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz",
)
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "testserver,localhost,127.0.0.1")
os.environ.setdefault("DJANGO_DEBUG", "false")
os.environ.setdefault("DJANGO_SSL_REDIRECT", "false")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("POSTGRES_DB", "neoskill")
os.environ.setdefault("POSTGRES_USER", "neoskill")
os.environ.setdefault("POSTGRES_PASSWORD", "dev-only-neoskill-postgres")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")

from neoskill.config.settings import *  # noqa: E402,F403
