from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course(*, is_free: bool = True, status: str = Course.Status.PUBLISHED) -> Course:
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
        status=status,
    )


def student_client() -> tuple[User, APIClient]:
    user = User.objects.create_user()
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def test_free_enrollment_is_active_and_idempotent():
    free_course = course()
    user, client = student_client()
    first = client.post("/api/v1/courses/python/enroll/free", format="json")
    second = client.post("/api/v1/courses/python/enroll/free", format="json")
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == Enrollment.Status.ACTIVE
    assert first.json()["next_path"] == "/learn/python"
    assert Enrollment.objects.filter(user=user, course=free_course).count() == 1


def test_paid_and_unpublished_courses_cannot_use_free_enrollment():
    course(is_free=False)
    _, client = student_client()
    assert client.post("/api/v1/courses/python/enroll/free", format="json").status_code == 400

    Course.objects.all().delete()
    Category.objects.all().delete()
    Instructor.objects.all().delete()
    course(status=Course.Status.DRAFT)
    assert client.post("/api/v1/courses/python/enroll/free", format="json").status_code == 404


def test_guest_and_admin_cannot_create_student_enrollment():
    course()
    assert APIClient().post("/api/v1/courses/python/enroll/free", format="json").status_code in {
        401,
        403,
    }
    admin_client = APIClient()
    admin_client.force_authenticate(user=User.objects.create_superuser("admin@example.com"))
    assert admin_client.post("/api/v1/courses/python/enroll/free", format="json").status_code == 403
    assert Enrollment.objects.count() == 0
