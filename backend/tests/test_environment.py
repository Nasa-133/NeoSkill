import pytest
from django.core.exceptions import ImproperlyConfigured

from neoskill.config.environment import load_environment


def valid_environment():
    return {
        "DJANGO_SECRET_KEY": "production-example-only-0123456789-ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "DJANGO_ALLOWED_HOSTS": "api.example.com",
        "CORS_ALLOWED_ORIGINS": "https://example.com",
    }


def test_defaults_are_production_and_debug_is_off():
    config = load_environment(valid_environment())
    assert config.mode == "production"
    assert config.debug is False


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_ENV", "prodution"),
        ("DJANGO_DEBUG", "yes"),
        ("DJANGO_DEBUG", "true"),
        ("DJANGO_SSL_REDIRECT", "1"),
        ("DJANGO_SECRET_KEY", ""),
        ("DJANGO_SECRET_KEY", "x" * 60),
        ("DJANGO_SECRET_KEY", "dev-only-" + "abcdefghij" * 6),
        ("DJANGO_ALLOWED_HOSTS", "*"),
        ("DJANGO_ALLOWED_HOSTS", ""),
        ("DJANGO_ALLOWED_HOSTS", "https://api.example.com"),
        ("DJANGO_ALLOWED_HOSTS", "api.example.com:8000"),
        ("CORS_ALLOWED_ORIGINS", "*"),
        ("CORS_ALLOWED_ORIGINS", "http://example.com"),
        ("CORS_ALLOWED_ORIGINS", "https://example.com/path"),
        ("CORS_ALLOWED_ORIGINS", "https://example.com/"),
        ("CORS_ALLOWED_ORIGINS", "https://user:password@example.com"),
        ("CORS_ALLOWED_ORIGINS", "https://example.com?query=1"),
        ("CORS_ALLOWED_ORIGINS", "https://example.com#fragment"),
        ("CORS_ALLOWED_ORIGINS", "https://example.com:99999"),
        ("CORS_ALLOWED_ORIGINS", "https://[invalid"),
    ],
)
def test_invalid_deployment_input_fails_closed(name, value):
    with pytest.raises(ImproperlyConfigured, match=name):
        load_environment({**valid_environment(), name: value})


def test_missing_environment_does_not_silently_enable_development():
    with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
        load_environment({})


def test_local_hosts_and_origins_are_explicit_and_deduplicated():
    config = load_environment(
        {
            **valid_environment(),
            "APP_ENV": "local",
            "DJANGO_ALLOWED_HOSTS": "localhost, 127.0.0.1, [::1],localhost",
            "CORS_ALLOWED_ORIGINS": "http://localhost:3000, http://[::1]:3000",
        }
    )
    assert config.allowed_hosts == ("localhost", "127.0.0.1", "[::1]")
    assert config.cors_origins == ("http://localhost:3000", "http://[::1]:3000")


def test_complete_postgresql_configuration_is_parsed():
    config = load_environment(
        {
            **valid_environment(),
            "POSTGRES_DB": "neoskill",
            "POSTGRES_USER": "neoskill_app",
            "POSTGRES_PASSWORD": "production-database-secret",
            "POSTGRES_HOST": "database.internal",
            "POSTGRES_PORT": "5432",
        }
    )
    assert config.database is not None
    assert config.database.name == "neoskill"
    assert config.database.port == 5432


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"POSTGRES_DB": "neoskill"}, "incomplete"),
        (
            {
                "POSTGRES_DB": "bad/name",
                "POSTGRES_USER": "neoskill",
                "POSTGRES_PASSWORD": "production-database-secret",
                "POSTGRES_HOST": "database.internal",
                "POSTGRES_PORT": "5432",
            },
            "POSTGRES_DB",
        ),
        (
            {
                "POSTGRES_DB": "neoskill",
                "POSTGRES_USER": "neoskill",
                "POSTGRES_PASSWORD": "production-database-secret",
                "POSTGRES_HOST": "https://database.internal",
                "POSTGRES_PORT": "5432",
            },
            "POSTGRES_HOST",
        ),
        (
            {
                "POSTGRES_DB": "neoskill",
                "POSTGRES_USER": "neoskill",
                "POSTGRES_PASSWORD": "production-database-secret",
                "POSTGRES_HOST": "database.internal",
                "POSTGRES_PORT": "70000",
            },
            "POSTGRES_PORT",
        ),
        (
            {
                "POSTGRES_DB": "neoskill",
                "POSTGRES_USER": "neoskill",
                "POSTGRES_PASSWORD": "dev-only-neoskill-postgres",
                "POSTGRES_HOST": "database.internal",
                "POSTGRES_PORT": "5432",
            },
            "POSTGRES_PASSWORD",
        ),
    ],
)
def test_invalid_postgresql_configuration_fails_closed(overrides, message):
    with pytest.raises(ImproperlyConfigured, match=message):
        load_environment({**valid_environment(), **overrides})


def email_environment():
    return {
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": "mailer@example.com",
        "EMAIL_HOST_PASSWORD": "mailer-secret",
        "EMAIL_FROM": "no-reply@example.com",
    }


def test_complete_email_configuration_is_parsed():
    config = load_environment({**valid_environment(), **email_environment()})
    assert config.email is not None
    assert config.email.port == 587
    assert config.email.use_tls is True


def test_email_configuration_is_optional():
    assert load_environment(valid_environment()).email is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"EMAIL_HOST": "smtp.example.com"}, "incomplete"),
        ({**email_environment(), "EMAIL_PORT": "not-a-number"}, "EMAIL_PORT"),
        ({**email_environment(), "EMAIL_PORT": "99999"}, "EMAIL_PORT"),
        ({**email_environment(), "EMAIL_FROM": "not-an-email"}, "EMAIL_FROM"),
    ],
)
def test_invalid_email_configuration_fails_closed(overrides, message):
    with pytest.raises(ImproperlyConfigured, match=message):
        load_environment({**valid_environment(), **overrides})


def test_frontend_url_must_be_absolute():
    assert load_environment(valid_environment()).frontend_url == "http://localhost:3000"
    trimmed = load_environment({**valid_environment(), "FRONTEND_URL": "https://neoskill.uz/"})
    assert trimmed.frontend_url == "https://neoskill.uz"
    with pytest.raises(ImproperlyConfigured, match="FRONTEND_URL"):
        load_environment({**valid_environment(), "FRONTEND_URL": "neoskill.uz"})
