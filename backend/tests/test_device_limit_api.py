import uuid

import pytest
from django.contrib.sessions.models import Session
from rest_framework.test import APIClient

from neoskill.identity.models import DeviceSession, User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"


def device() -> str:
    return str(uuid.uuid4())


def sign_in(client: APIClient, device_id: str, name: str = "Brauzer", revoke: str | None = None):
    body: dict[str, object] = {
        "email": "student@example.com",
        "password": PASSWORD,
        "device_id": device_id,
        "device_name": name,
    }
    if revoke:
        body["revoke_device_session_id"] = revoke
    return client.post("/api/v1/auth/login", body, format="json")


@pytest.fixture
def account() -> User:
    return User.objects.create_user(email="student@example.com", password=PASSWORD)


def test_registration_records_the_first_device(account):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/register",
        {
            "email": "fresh@example.com",
            "password": PASSWORD,
            "device_id": device(),
            "device_name": "MacBook — Chrome",
        },
        format="json",
    )
    assert response.status_code == 201
    record = DeviceSession.objects.get(user__email="fresh@example.com")
    assert record.device_name == "MacBook — Chrome"


def test_two_devices_may_be_signed_in_at_once(account):
    first, second = APIClient(), APIClient()
    assert sign_in(first, device(), "MacBook").status_code == 200
    assert sign_in(second, device(), "iPhone").status_code == 200

    assert DeviceSession.objects.filter(user=account).count() == 2
    assert first.get("/api/v1/auth/session").status_code == 200
    assert second.get("/api/v1/auth/session").status_code == 200


def test_a_third_device_is_refused_and_lists_the_current_ones(account):
    sign_in(APIClient(), device(), "MacBook")
    sign_in(APIClient(), device(), "iPhone")

    third = APIClient()
    response = sign_in(third, device(), "Windows")

    assert response.status_code == 409
    assert response.json()["code"] == "device_limit"
    names = {item["name"] for item in response.json()["devices"]}
    assert names == {"MacBook", "iPhone"}
    # The refused browser must not hold a session.
    assert third.get("/api/v1/auth/session").status_code in {401, 403}
    assert DeviceSession.objects.filter(user=account).count() == 2


def test_releasing_a_device_signs_that_browser_out_and_lets_the_new_one_in(account):
    first, second, third = APIClient(), APIClient(), APIClient()
    sign_in(first, device(), "MacBook")
    sign_in(second, device(), "iPhone")

    refused = sign_in(third, device(), "Windows")
    target = next(item for item in refused.json()["devices"] if item["name"] == "MacBook")

    allowed = sign_in(third, device(), "Windows", revoke=target["id"])
    assert allowed.status_code == 200

    # The released browser is now signed out; the other two still work.
    assert first.get("/api/v1/auth/session").status_code in {401, 403}
    assert second.get("/api/v1/auth/session").status_code == 200
    assert third.get("/api/v1/auth/session").status_code == 200
    assert set(
        DeviceSession.objects.filter(user=account).values_list("device_name", flat=True)
    ) == {
        "iPhone",
        "Windows",
    }


def test_the_same_device_reconnects_without_consuming_a_slot(account):
    known = device()
    first = APIClient()
    sign_in(first, known, "MacBook")
    sign_in(APIClient(), device(), "iPhone")

    again = APIClient()
    assert sign_in(again, known, "MacBook").status_code == 200
    assert DeviceSession.objects.filter(user=account).count() == 2


def test_logout_frees_the_slot(account):
    first, second = APIClient(), APIClient()
    sign_in(first, device(), "MacBook")
    sign_in(second, device(), "iPhone")

    assert first.post("/api/v1/auth/logout").status_code == 204
    assert DeviceSession.objects.filter(user=account).count() == 1
    assert sign_in(APIClient(), device(), "Windows").status_code == 200


def test_a_person_can_list_and_release_their_own_devices(account):
    first, second = APIClient(), APIClient()
    sign_in(first, device(), "MacBook")
    sign_in(second, device(), "iPhone")

    listed = first.get("/api/v1/auth/devices")
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    assert sum(1 for item in listed.json() if item["current"]) == 1

    other = next(item for item in listed.json() if not item["current"])
    assert first.delete(f"/api/v1/auth/devices?id={other['id']}").status_code == 204
    assert second.get("/api/v1/auth/session").status_code in {401, 403}
    assert len(first.get("/api/v1/auth/devices").json()) == 1


def test_a_device_of_another_account_cannot_be_released(account):
    other = User.objects.create_user(email="other@example.com", password=PASSWORD)
    victim = APIClient()
    victim.post(
        "/api/v1/auth/login",
        {
            "email": "other@example.com",
            "password": PASSWORD,
            "device_id": device(),
            "device_name": "Victim",
        },
        format="json",
    )
    target = DeviceSession.objects.get(user=other)

    attacker = APIClient()
    sign_in(attacker, device(), "Attacker")
    assert attacker.delete(f"/api/v1/auth/devices?id={target.pk}").status_code == 404
    assert DeviceSession.objects.filter(pk=target.pk).exists()


def test_a_stale_row_does_not_block_a_new_sign_in(account):
    sign_in(APIClient(), device(), "MacBook")
    sign_in(APIClient(), device(), "iPhone")

    # Simulate an expired Django session while the tracking row lingers.
    stale = DeviceSession.objects.filter(user=account).first()
    assert stale is not None
    Session.objects.filter(session_key=stale.session_key).delete()

    assert sign_in(APIClient(), device(), "Windows").status_code == 200


def test_login_without_a_device_id_is_rejected(account):
    response = APIClient().post(
        "/api/v1/auth/login",
        {"email": "student@example.com", "password": PASSWORD},
        format="json",
    )
    assert response.status_code == 400
