from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"
DEVICE = "55555555-5555-4555-8555-555555555555"


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def course(slug: str, *, free: bool) -> Course:
    category, _ = Category.objects.get_or_create(name="Referral", slug="referral")
    instructor, _ = Instructor.objects.get_or_create(
        name="Referral Teacher", slug="referral-teacher", defaults={"title": "Teacher"}
    )
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=f"Course {slug}",
        slug=slug,
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=free,
        price=None if free else Decimal("200000.00"),
        status=Course.Status.PUBLISHED,
    )


def register(email: str, referral_code: str = ""):
    return APIClient().post(
        "/api/v1/auth/register",
        {
            "email": email,
            "password": PASSWORD,
            "device_id": DEVICE,
            "referral_code": referral_code,
        },
        format="json",
    )


def test_registration_attributes_once_and_snapshots_the_admin_discount():
    inviter = User.objects.create_user(email="inviter@example.com", password=PASSWORD)
    inviter.referral_discount_percent = 15
    inviter.save(update_fields=("referral_discount_percent",))

    response = register("new@example.com", inviter.referral_code.lower())

    assert response.status_code == 201
    referred = User.objects.get(email="new@example.com")
    assert referred.referred_by == inviter
    assert referred.referral_discount_applied == 15
    assert referred.referral_code != inviter.referral_code

    inviter.referral_discount_percent = 25
    inviter.save(update_fields=("referral_discount_percent",))
    referred.refresh_from_db()
    assert referred.referral_discount_applied == 15


def test_unknown_or_malformed_referral_does_not_create_an_account():
    unknown = register("unknown@example.com", "23456789ABCD")
    malformed = register("malformed@example.com", "bad code")

    assert unknown.status_code == 400
    assert malformed.status_code == 400
    assert not User.objects.filter(
        email__in=("unknown@example.com", "malformed@example.com")
    ).exists()


def test_existing_account_cannot_be_reassigned_and_database_rejects_self_reference():
    original = User.objects.create_user(email="original@example.com", password=PASSWORD)
    account = User.objects.create_user(
        email="member@example.com",
        password=PASSWORD,
        referred_by=original,
        referral_discount_applied=10,
    )
    other = User.objects.create_user(email="other@example.com", password=PASSWORD)

    login = APIClient().post(
        "/api/v1/auth/login",
        {
            "email": account.email,
            "password": PASSWORD,
            "device_id": DEVICE,
            "referral_code": other.referral_code,
        },
        format="json",
    )
    assert login.status_code == 200
    account.refresh_from_db()
    assert account.referred_by == original

    account.referred_by = account
    with pytest.raises(IntegrityError), transaction.atomic():
        account.save(update_fields=("referred_by",))


def test_public_offer_and_member_summary_expose_only_intended_data():
    inviter = User.objects.create_user(
        email="inviter@example.com", password=PASSWORD, referral_discount_percent=20
    )
    referred = User.objects.create_user(
        email="member@example.com", password=PASSWORD, referred_by=inviter
    )
    Enrollment.objects.create(user=referred, course=course("free", free=True))

    offer = APIClient().get(f"/api/v1/referrals/{inviter.referral_code}")
    summary = client_for(inviter).get("/api/v1/me/referral")

    assert offer.status_code == 200
    assert offer.json() == {
        "code": inviter.referral_code,
        "inviter_name": "",
        "discount_percent": 20,
    }
    assert "email" not in offer.json()
    assert summary.status_code == 200
    assert summary.json()["referred_count"] == 1
    assert summary.json()["referred_with_access"] == 1
    assert summary.json()["free_access_count"] == 1
    assert summary.json()["paid_access_count"] == 0
    assert summary.json()["applied_discount_percent"] == 0


def test_admin_controls_future_discount_and_sees_people_and_course_access():
    admin = User.objects.create_superuser("admin@example.com", PASSWORD)
    inviter = User.objects.create_user(email="inviter@example.com", password=PASSWORD)
    first = User.objects.create_user(
        email="first@example.com",
        password=PASSWORD,
        referred_by=inviter,
        referral_discount_applied=5,
    )
    second = User.objects.create_user(
        email="second@example.com", password=PASSWORD, referred_by=inviter
    )
    Enrollment.objects.create(user=first, course=course("free", free=True))
    Enrollment.objects.create(user=first, course=course("paid", free=False))
    Enrollment.objects.create(user=second, course=course("paid-two", free=False))
    client = client_for(admin)

    changed = client.patch(
        f"/api/v1/admin/referrals/{inviter.pk}", {"discount_percent": 30}, format="json"
    )
    listed = client.get("/api/v1/admin/referrals?search=inviter").json()
    detail = client.get(f"/api/v1/admin/referrals/{inviter.pk}").json()

    assert changed.status_code == 200
    assert changed.json()["discount_percent"] == 30
    assert len(listed) == 1
    assert listed[0]["referred_count"] == 2
    assert listed[0]["referred_with_access"] == 2
    assert listed[0]["free_access_count"] == 1
    assert listed[0]["paid_access_count"] == 2
    assert {item["email"] for item in detail["referred_users"]} == {
        "first@example.com",
        "second@example.com",
    }
    assert (
        client.patch(
            f"/api/v1/admin/referrals/{inviter.pk}", {"discount_percent": 101}, format="json"
        ).status_code
        == 400
    )
    first.refresh_from_db()
    assert first.referral_discount_applied == 5


def test_non_admin_cannot_read_or_change_referral_reports():
    student = User.objects.create_user(email="student@example.com", password=PASSWORD)
    client = client_for(student)
    assert client.get("/api/v1/admin/referrals").status_code == 403
    assert client.get(f"/api/v1/admin/referrals/{student.pk}").status_code == 403
    assert (
        client.patch(
            f"/api/v1/admin/referrals/{student.pk}", {"discount_percent": 20}, format="json"
        ).status_code
        == 403
    )


def test_paid_request_snapshots_discounted_amount_and_is_idempotent():
    inviter = User.objects.create_user(email="inviter@example.com", password=PASSWORD)
    referred = User.objects.create_user(
        email="member@example.com",
        password=PASSWORD,
        referred_by=inviter,
        referral_discount_applied=25,
    )
    paid = course("discounted", free=False)
    client = client_for(referred)

    first = client.post(f"/api/v1/courses/{paid.slug}/enrollment-requests", {}, format="json")
    second = client.post(f"/api/v1/courses/{paid.slug}/enrollment-requests", {}, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    request = EnrollmentRequest.objects.get(user=referred, course=paid)
    assert request.list_price == Decimal("200000.00")
    assert request.referral_discount_percent == 25
    assert request.requested_price == Decimal("150000.00")


def test_authenticated_course_detail_shows_the_effective_referral_price():
    inviter = User.objects.create_user(email="inviter@example.com", password=PASSWORD)
    referred = User.objects.create_user(
        email="member@example.com",
        password=PASSWORD,
        referred_by=inviter,
        referral_discount_applied=10,
    )
    paid = course("detail", free=False)

    guest = APIClient().get(f"/api/v1/courses/{paid.slug}").json()
    member = client_for(referred).get(f"/api/v1/courses/{paid.slug}").json()

    assert guest["referral_discount_percent"] == 0
    assert guest["discounted_price"] == "200000.00"
    assert member["referral_discount_percent"] == 10
    assert member["discounted_price"] == "180000.00"
