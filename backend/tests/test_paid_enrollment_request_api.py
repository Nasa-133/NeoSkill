from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def paid_course(*, is_free: bool = False) -> Course:
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
        is_free=is_free,
        price=None if is_free else Decimal("100000.00"),
        status=Course.Status.PUBLISHED,
    )


def verified_student() -> tuple[User, APIClient]:
    user = User.objects.create_user(email="student@example.com", password="Str0ng-Passw0rd")
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def test_verified_student_creates_one_pending_request_idempotently():
    course = paid_course()
    user, client = verified_student()
    first = client.post(
        "/api/v1/courses/python/enrollment-requests",
        {"note": "  I want to learn.  "},
        format="json",
    )
    second = client.post("/api/v1/courses/python/enrollment-requests", {}, format="json")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == EnrollmentRequest.Status.PENDING
    assert first.json()["note"] == "I want to learn."
    assert EnrollmentRequest.objects.filter(user=user, course=course).count() == 1


def test_paid_request_accepts_the_empty_optional_note_sent_by_the_browser():
    paid_course()
    _, client = verified_student()

    response = client.post(
        "/api/v1/courses/python/enrollment-requests", {"note": ""}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["note"] == ""


def test_free_course_rejects_a_paid_request():
    paid_course()
    user = User.objects.create_user(email="free@example.com")
    client = APIClient()
    client.force_authenticate(user=user)

    Course.objects.update(is_free=True, price=None)
    assert (
        client.post("/api/v1/courses/python/enrollment-requests", {}, format="json").status_code
        == 400
    )


def test_active_enrollment_prevents_paid_request():
    course = paid_course()
    user, client = verified_student()
    Enrollment.objects.create(user=user, course=course)
    assert (
        client.post("/api/v1/courses/python/enrollment-requests", {}, format="json").status_code
        == 409
    )
    assert EnrollmentRequest.objects.count() == 0
