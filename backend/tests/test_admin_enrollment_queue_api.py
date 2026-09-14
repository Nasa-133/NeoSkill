from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course() -> Course:
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title="Python",
        slug="python",
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=False,
        price=Decimal("100000.00"),
        status=Course.Status.PUBLISHED,
    )


def pending_request() -> EnrollmentRequest:
    user = User.objects.create_user(
        email="queue-student@example.com", first_name="Aziza", last_name="Sobirova"
    )
    return EnrollmentRequest.objects.create(user=user, course=course())


def admin_client() -> tuple[User, APIClient]:
    admin = User.objects.create_superuser("admin@example.com")
    client = APIClient()
    client.force_authenticate(user=admin)
    return admin, client


def test_admin_queue_defaults_to_pending_and_exposes_detail_status():
    request = pending_request()
    admin, client = admin_client()
    rejected_user = User.objects.create_user()
    rejected = EnrollmentRequest.objects.create(
        user=rejected_user,
        course=request.course,
        status=EnrollmentRequest.Status.REJECTED,
        reviewed_by=admin,
        reviewed_at=timezone.now(),
    )

    queue = client.get("/api/v1/admin/enrollment-requests")
    assert queue.status_code == 200
    assert [item["id"] for item in queue.json()] == [str(request.pk)]
    assert queue.json()[0]["user_email"] == "queue-student@example.com"
    assert queue.json()[0]["user_name"] == "Aziza Sobirova"
    detail = client.get(f"/api/v1/admin/enrollment-requests/{request.pk}")
    assert detail.status_code == 200
    assert detail.json()["course_slug"] == "python"
    rejected_queue = client.get("/api/v1/admin/enrollment-requests", {"status": "REJECTED"})
    assert [item["id"] for item in rejected_queue.json()] == [str(rejected.pk)]


def test_approve_is_idempotent_and_creates_active_enrollment():
    request = pending_request()
    admin, client = admin_client()
    url = f"/api/v1/admin/enrollment-requests/{request.pk}/approve"
    first = client.post(url, format="json")
    second = client.post(url, format="json")
    assert first.status_code == second.status_code == 200
    request.refresh_from_db()
    assert request.status == EnrollmentRequest.Status.APPROVED
    assert request.reviewed_by == admin
    assert request.reviewed_at is not None
    enrollment = Enrollment.objects.get(user=request.user, course=request.course)
    assert enrollment.status == Enrollment.Status.ACTIVE
    assert Enrollment.objects.filter(user=request.user, course=request.course).count() == 1


def test_reject_is_idempotent_and_cannot_later_be_approved():
    request = pending_request()
    _, client = admin_client()
    reject_url = f"/api/v1/admin/enrollment-requests/{request.pk}/reject"
    assert client.post(reject_url, format="json").status_code == 200
    assert client.post(reject_url, format="json").status_code == 200
    assert (
        client.post(
            f"/api/v1/admin/enrollment-requests/{request.pk}/approve", format="json"
        ).status_code
        == 409
    )
    assert Enrollment.objects.count() == 0


def test_non_admin_cannot_read_or_decide_requests():
    request = pending_request()
    student = APIClient()
    student.force_authenticate(user=request.user)
    assert student.get("/api/v1/admin/enrollment-requests").status_code == 403
    assert (
        student.post(
            f"/api/v1/admin/enrollment-requests/{request.pk}/approve", format="json"
        ).status_code
        == 403
    )
