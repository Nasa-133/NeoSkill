from smtplib import SMTPAuthenticationError
from unittest.mock import Mock

import pytest
from django.core import mail
from rest_framework.test import APIClient

from neoskill.identity.models import User
from neoskill.platform.models import PlatformSettings
from neoskill.platform.services import decrypt_password

pytestmark = pytest.mark.django_db


def admin_client():
    user = User.objects.create_superuser("settings-owner@example.com", "Strong-Password91!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def smtp_config():
    return {
        "smtp_source": "ADMIN",
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "smtp_security": "SSL",
        "smtp_username": "mailer@example.com",
        "smtp_password": "secret-mail-password",
        "smtp_from_email": "hello@example.com",
    }


def test_settings_default_is_public_but_management_requires_admin():
    guest = APIClient()
    assert guest.get("/api/v1/settings/public").json()["platform_name"] == "NeoSkill"
    assert guest.get("/api/v1/admin/settings").status_code == 403
    student = User.objects.create_user("learner@example.com", "Strong-Password91!")
    guest.force_authenticate(user=student)
    assert guest.patch("/api/v1/admin/settings", {"platform_name": "Changed"}).status_code == 403
    assert (
        guest.post("/api/v1/admin/settings/test-email", {"email": student.email}).status_code == 403
    )
    assert not PlatformSettings.objects.exists()


def test_admin_changes_persist_and_only_public_fields_are_public():
    client = admin_client()
    response = client.patch(
        "/api/v1/admin/settings",
        {
            **smtp_config(),
            "company_name": "Neo Academy",
            "support_telegram": "https://t.me/NeoHelp",
            "support_phone": "+998 90 123 45 67",
            "support_email": "help@example.com",
        },
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["smtp_password_set"] is True
    assert "smtp_password" not in response.json()
    assert "secret-mail-password" not in response.content.decode()
    config = PlatformSettings.objects.get()
    assert config.smtp_password_encrypted != smtp_config()["smtp_password"]
    assert decrypt_password(config.smtp_password_encrypted) == smtp_config()["smtp_password"]
    public = APIClient().get("/api/v1/settings/public").json()
    assert public["company_name"] == "Neo Academy"
    assert public["support_telegram"] == "NeoHelp"
    assert not any(key.startswith("smtp_") for key in public)
    assert client.get("/api/v1/admin/settings").json()["company_name"] == "Neo Academy"
    assert (
        client.patch(
            "/api/v1/admin/settings", {"smtp_password": "", "footer_text": "New"}, format="json"
        ).status_code
        == 200
    )
    config.refresh_from_db()
    assert decrypt_password(config.smtp_password_encrypted) == smtp_config()["smtp_password"]


@pytest.mark.parametrize(
    "payload",
    [
        {"support_telegram": "javascript:alert(1)"},
        {"support_email": "invalid"},
        {"smtp_source": "ADMIN"},
        {**smtp_config(), "smtp_port": 70000},
        {**smtp_config(), "smtp_host": "https://smtp.example.com"},
        {"platform_name": "Bad\r\nName"},
    ],
)
def test_invalid_settings_are_rejected_atomically(payload):
    assert admin_client().patch("/api/v1/admin/settings", payload, format="json").status_code == 400
    assert not PlatformSettings.objects.exists()


def test_environment_values_are_visible_but_secret_is_write_only(settings):
    settings.EMAIL_HOST = "existing.example.com"
    settings.EMAIL_HOST_USER = "existing@example.com"
    settings.EMAIL_HOST_PASSWORD = "existing-secret"
    settings.EMAIL_PORT = 587
    settings.EMAIL_USE_TLS = True
    settings.DEFAULT_FROM_EMAIL = "existing@example.com"
    client = admin_client()
    original = client.get("/api/v1/admin/settings").json()
    assert original["smtp_host"] == "existing.example.com"
    assert original["smtp_password_set"] is True
    assert "existing-secret" not in str(original)
    response = client.patch(
        "/api/v1/admin/settings", {**original, "smtp_source": "ADMIN"}, format="json"
    )
    assert response.status_code == 200
    assert (
        decrypt_password(PlatformSettings.objects.get().smtp_password_encrypted)
        == "existing-secret"
    )


def test_reset_and_test_email_use_saved_smtp(monkeypatch):
    client = admin_client()
    assert client.patch("/api/v1/admin/settings", smtp_config(), format="json").status_code == 200
    connection = Mock()
    connection.send_messages.return_value = 1
    factory = Mock(return_value=connection)
    monkeypatch.setattr("neoskill.platform.services.get_connection", factory)
    response = client.post(
        "/api/v1/admin/settings/test-email", {"email": "check@example.com"}, format="json"
    )
    assert response.status_code == 200
    assert factory.call_args.kwargs["host"] == "smtp.example.com"
    assert factory.call_args.kwargs["use_ssl"] is True
    assert factory.call_args.kwargs["password"] == "secret-mail-password"
    assert connection.send_messages.call_args.args[0][0].to == ["check@example.com"]
    response = APIClient().post(
        "/api/v1/auth/password-reset", {"email": "settings-owner@example.com"}, format="json"
    )
    assert response.status_code == 202
    message = connection.send_messages.call_args.args[0][0]
    assert message.from_email == "hello@example.com"
    assert "/reset-password?uid=" in message.body


def test_mail_failures_are_actionable_without_leaking_secrets(monkeypatch):
    client = admin_client()
    client.patch("/api/v1/admin/settings", smtp_config(), format="json")

    def fail(**kwargs):
        raise SMTPAuthenticationError(535, b"secret-mail-password")

    monkeypatch.setattr("neoskill.platform.services.get_connection", fail)
    response = client.post(
        "/api/v1/admin/settings/test-email", {"email": "check@example.com"}, format="json"
    )
    assert response.status_code == 502
    assert "secret-mail-password" not in response.content.decode()
    known = APIClient().post(
        "/api/v1/auth/password-reset", {"email": "settings-owner@example.com"}, format="json"
    )
    unknown = APIClient().post(
        "/api/v1/auth/password-reset", {"email": "unknown@example.com"}, format="json"
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_default_mail_backend_still_works_and_console_does_not_fake_delivery(settings):
    client = admin_client()
    response = client.post(
        "/api/v1/admin/settings/test-email", {"email": "check@example.com"}, format="json"
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    assert (
        client.post(
            "/api/v1/admin/settings/test-email", {"email": "check@example.com"}, format="json"
        ).status_code
        == 400
    )


def test_settings_mutation_requires_csrf_for_real_session():
    user = User.objects.create_superuser("csrf-settings@example.com", "Strong-Password91!")
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(user)
    assert (
        client.patch(
            "/api/v1/admin/settings", {"company_name": "Changed"}, format="json"
        ).status_code
        == 403
    )
