import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from neoskill.config.environment import load_environment

BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env", override=False)
environment = load_environment(os.environ)

SECRET_KEY = environment.secret_key
DEBUG = environment.debug
NEOSKILL_ENVIRONMENT = environment.mode
ALLOWED_HOSTS = list(environment.allowed_hosts)
ROOT_URLCONF = "neoskill.config.urls"
WSGI_APPLICATION = "neoskill.config.wsgi.application"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "corsheaders",
    "neoskill.identity",
    "neoskill.catalog",
    "neoskill.enrollment",
    "neoskill.learning",
    "neoskill.assessment",
    "neoskill.health",
    "neoskill.platform",
    "neoskill.referral",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if environment.database is None:
    # Liveness can start without persistence; readiness and DB commands fail closed.
    DATABASES: dict[str, Any] = {}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": environment.database.name,
            "USER": environment.database.user,
            "PASSWORD": environment.database.password,
            "HOST": environment.database.host,
            "PORT": environment.database.port,
            "CONN_MAX_AGE": 0 if environment.mode == "test" else 60,
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": 5},
        }
    }
AUTH_USER_MODEL = "identity.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_DEVICE_SESSION_LIMIT = 2
FRONTEND_URL = environment.frontend_url
MEDIA_ROOT = environment.media_root
# Uploads are served back through the same /api/v1 path the frontend already proxies.
MEDIA_URL = "/api/v1/media/"
UPLOAD_MAX_BYTES = 2 * 1024 * 1024
UPLOAD_ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PASSWORD_RESET_TIMEOUT = 60 * 60 * 2  # the reset link stays valid for two hours

if environment.email is None:
    # Without SMTP credentials the reset mail is printed to the container log.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "no-reply@neoskill.local"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = environment.email.host
    EMAIL_PORT = environment.email.port
    EMAIL_HOST_USER = environment.email.user
    EMAIL_HOST_PASSWORD = environment.email.password
    EMAIL_USE_TLS = environment.email.use_tls
    EMAIL_TIMEOUT = 10
    DEFAULT_FROM_EMAIL = environment.email.from_address
USE_TZ = True
TIME_ZONE = "Asia/Tashkent"
LANGUAGE_CODE = "uz"
APPEND_SLASH = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "neoskill.config.http_errors.api_exception_handler",
}

CORS_ALLOWED_ORIGINS = list(environment.cors_origins)
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/"
SECURE_SSL_REDIRECT = environment.ssl_redirect
SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]
# Start with a one-hour production policy; increase it only after HTTPS is proven stable.
SECURE_HSTS_SECONDS = 3600 if environment.mode == "production" and environment.ssl_redirect else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# Subdomain coverage and browser preloading require deployment-owned DNS guarantees.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = environment.mode == "production"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = environment.mode == "production"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = list(environment.cors_origins)
CSRF_FAILURE_VIEW = "neoskill.config.http_errors.csrf_failure"
X_FRAME_OPTIONS = "DENY"
# Production exposes the backend only through the frontend/reverse-proxy network. This lets
# SecurityMiddleware recognize the original HTTPS request and avoids an SSL redirect loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
