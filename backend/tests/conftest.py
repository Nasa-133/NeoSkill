import os

import django

# Tests use the dedicated PostgreSQL database created by pytest-django.
os.environ["APP_ENV"] = "test"
os.environ["DJANGO_SECRET_KEY"] = (
    "test-only-neoskill-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz"
)
os.environ["DJANGO_ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"
os.environ["DJANGO_DEBUG"] = "false"
os.environ["DJANGO_SSL_REDIRECT"] = "false"
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:3000"
os.environ.setdefault("POSTGRES_DB", "neoskill")
os.environ.setdefault("POSTGRES_USER", "neoskill")
os.environ.setdefault("POSTGRES_PASSWORD", "dev-only-neoskill-postgres")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ["DJANGO_SETTINGS_MODULE"] = "neoskill.config.test_settings"
django.setup()
