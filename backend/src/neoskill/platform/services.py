import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from neoskill.platform.models import PlatformSettings


def current_settings() -> PlatformSettings:
    return PlatformSettings.objects.filter(pk=1).first() or PlatformSettings(pk=1)


def _cipher() -> Fernet:
    key = hashlib.sha256(("neoskill:smtp:v1:" + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_password(value: str) -> str:
    return _cipher().encrypt(value.encode()).decode() if value else ""


def decrypt_password(value: str) -> str:
    return _cipher().decrypt(value.encode()).decode() if value else ""


def send_platform_email(*, subject: str, message: str, recipient: str) -> int:
    config = current_settings()
    if config.smtp_source == "ADMIN":
        connection = get_connection(
            backend="django.core.mail.backends.smtp.EmailBackend",
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=decrypt_password(config.smtp_password_encrypted),
            use_tls=config.smtp_security == "TLS",
            use_ssl=config.smtp_security == "SSL",
            timeout=10,
            fail_silently=False,
        )
        sender = config.smtp_from_email
    else:
        connection = get_connection(fail_silently=False)
        sender = settings.DEFAULT_FROM_EMAIL
    return EmailMessage(subject, message, sender, [recipient], connection=connection).send()
