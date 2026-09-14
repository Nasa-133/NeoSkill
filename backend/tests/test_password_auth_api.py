from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, BrokenBarrierError

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.db import close_old_connections
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from neoskill.identity.models import LoginThrottle, User
from neoskill.identity.session_auth import LOGIN_ATTEMPT_LIMIT

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"
DEVICE = "11111111-1111-4111-8111-111111111111"


def account(email: str = "student@example.com", **extra: object) -> User:
    return User.objects.create_user(email=email, password=PASSWORD, **extra)


def test_registration_opens_a_session_and_returns_the_profile():
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "New@Example.com",
            "password": PASSWORD,
            "first_name": "Aziza",
            "device_id": DEVICE,
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "new@example.com"
    assert response.json()["user"]["role"] == User.Role.STUDENT
    # The session cookie is live straight away.
    assert client.get("/api/v1/auth/session").status_code == 200


def test_registration_rejects_a_duplicate_email_case_insensitively():
    account("taken@example.com")
    response = APIClient().post(
        "/api/v1/auth/register",
        {"email": "TAKEN@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.json()


def test_registration_rejects_a_weak_password():
    response = APIClient().post(
        "/api/v1/auth/register",
        {"email": "weak@example.com", "password": "12345678", "device_id": DEVICE},
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.json()


def test_registration_rejects_password_similar_to_account():
    response = APIClient().post(
        "/api/v1/auth/register",
        {
            "email": "UniqueLearner92@example.com",
            "password": "UniqueLearner92!",
            "device_id": DEVICE,
        },
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.json()
    assert not User.objects.filter(email="uniquelearner92@example.com").exists()


def test_login_succeeds_and_logout_clears_the_session():
    account()
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login",
        {"email": "STUDENT@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "student@example.com"
    assert client.get("/api/v1/auth/session").status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/session").status_code in {401, 403}


def test_login_hides_whether_the_account_exists():
    account()
    client = APIClient()
    wrong_password = client.post(
        "/api/v1/auth/login",
        {"email": "student@example.com", "password": "Wrong-Passw0rd!", "device_id": DEVICE},
        format="json",
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        {"email": "nobody@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert wrong_password.status_code == unknown_email.status_code == 400
    assert wrong_password.json() == unknown_email.json()


def test_blocked_account_cannot_sign_in():
    user = account()
    user.is_active = False
    user.save(update_fields=("is_active",))
    response = APIClient().post(
        "/api/v1/auth/login",
        {"email": user.email, "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert response.status_code == 400


def test_repeated_failures_are_throttled():
    account()
    client = APIClient()
    for _ in range(LOGIN_ATTEMPT_LIMIT):
        client.post(
            "/api/v1/auth/login",
            {"email": "student@example.com", "password": "Wrong-Passw0rd!", "device_id": DEVICE},
            format="json",
        )
    blocked = client.post(
        "/api/v1/auth/login",
        {"email": "student@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "600"


def test_successful_login_clears_the_throttle_counter():
    account()
    client = APIClient()
    client.post(
        "/api/v1/auth/login",
        {"email": "student@example.com", "password": "Wrong-Passw0rd!", "device_id": DEVICE},
        format="json",
    )
    assert LoginThrottle.objects.exists()
    client.post(
        "/api/v1/auth/login",
        {"email": "student@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert not LoginThrottle.objects.exists()


def test_password_reset_sends_a_link_and_accepts_it_once():
    user = account("reset@example.com")
    client = APIClient()

    requested = client.post(
        "/api/v1/auth/password-reset", {"email": "reset@example.com"}, format="json"
    )
    assert requested.status_code == 202
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    assert "/reset-password?uid=" in body

    query = body.split("/reset-password?", 1)[1].split()[0]
    fields = dict(pair.split("=", 1) for pair in query.split("&"))

    confirmed = client.post(
        "/api/v1/auth/password-reset/confirm",
        {"uid": fields["uid"], "token": fields["token"], "password": "Brand-New-Passw0rd!"},
        format="json",
    )
    assert confirmed.status_code == 200

    user.refresh_from_db()
    assert user.check_password("Brand-New-Passw0rd!")

    # The token is single use: the changed password invalidates it.
    replayed = client.post(
        "/api/v1/auth/password-reset/confirm",
        {"uid": fields["uid"], "token": fields["token"], "password": "Another-Passw0rd!"},
        format="json",
    )
    assert replayed.status_code == 400


def test_password_reset_does_not_reveal_unknown_emails():
    response = APIClient().post(
        "/api/v1/auth/password-reset", {"email": "nobody@example.com"}, format="json"
    )
    assert response.status_code == 202
    assert mail.outbox == []


def test_password_reset_rejects_a_tampered_token():
    account("tamper@example.com")
    client = APIClient()
    client.post("/api/v1/auth/password-reset", {"email": "tamper@example.com"}, format="json")
    query = mail.outbox[0].body.split("/reset-password?", 1)[1].split()[0]
    fields = dict(pair.split("=", 1) for pair in query.split("&"))

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        {"uid": fields["uid"], "token": fields["token"][:-1] + "x", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 400


def test_session_endpoint_requires_authentication():
    assert APIClient().get("/api/v1/auth/session").status_code in {401, 403}


@pytest.mark.parametrize("decoded_uid", ["not-a-uuid", "123", "", "\ufffd"])
def test_password_reset_rejects_malformed_identity(decoded_uid):
    response = APIClient().post(
        "/api/v1/auth/password-reset/confirm",
        {
            "uid": urlsafe_base64_encode(force_bytes(decoded_uid)),
            "token": "invalid-token",
            "password": PASSWORD,
        },
        format="json",
    )
    assert response.status_code == 400


def test_password_reset_expires_after_two_hours(monkeypatch):
    user = account()
    token = default_token_generator.make_token(user)
    later = default_token_generator._now() + timedelta(hours=2, seconds=1)
    monkeypatch.setattr(default_token_generator, "_now", lambda: later)
    response = APIClient().post(
        "/api/v1/auth/password-reset/confirm",
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": token,
            "password": "Brand-New-Passw0rd!",
        },
        format="json",
    )
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_password_reset_validates_password_against_account():
    user = account("UniqueLearner92@example.com")
    payload = {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": default_token_generator.make_token(user),
        "password": "UniqueLearner92!",
    }
    client = APIClient()
    response = client.post("/api/v1/auth/password-reset/confirm", payload, format="json")
    assert response.status_code == 400
    assert "password" in response.json()
    user.refresh_from_db()
    assert user.check_password(PASSWORD)
    # Validation must leave the reset link usable with a suitable password.
    payload["password"] = "Brand-New-Passw0rd!"
    assert (
        client.post("/api/v1/auth/password-reset/confirm", payload, format="json").status_code
        == 200
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_password_reset_accepts_only_one_request(monkeypatch):
    user = account()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    check_token = default_token_generator.check_token
    simultaneous_checks = Barrier(2)

    def synchronized_check(*args, **kwargs):
        # Without a row lock, both requests reach validation with the old password.
        # With serialization, the first request times out here and commits before
        # the second request reads the updated account and rejects the spent token.
        try:
            simultaneous_checks.wait(timeout=2)
        except BrokenBarrierError:
            pass
        return check_token(*args, **kwargs)

    monkeypatch.setattr(default_token_generator, "check_token", synchronized_check)

    def reset(password):
        close_old_connections()
        try:
            response = APIClient().post(
                "/api/v1/auth/password-reset/confirm",
                {"uid": uid, "token": token, "password": password},
                format="json",
            )
            return response.status_code, password
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reset, ["First-New-Passw0rd!", "Second-New-Passw0rd!"]))
    assert sorted(status for status, _ in results) == [200, 400]
    user.refresh_from_db()
    winner = next(password for status, password in results if status == 200)
    assert user.check_password(winner)
