import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def published_course(*, slug: str, is_free: bool) -> Course:
    category = Category.objects.create(name=f"{slug} category", slug=f"{slug}-category")
    instructor = Instructor.objects.create(
        name=f"{slug} instructor", slug=f"{slug}-instructor", title="Mentor"
    )
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=slug.replace("-", " ").title(),
        slug=slug,
        short_description="Amaliy kurs",
        description="Kurs tavsifi",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=is_free,
        price=None if is_free else "250000.00",
        status=Course.Status.PUBLISHED,
        what_you_will_learn=["Bir", "Ikki", "Uch"],
        audience=["Bir", "Ikki", "Uch"],
        requirements=["Kompyuter"],
    )


def state(client: APIClient, course: Course) -> str:
    response = client.get(f"/api/v1/courses/{course.slug}")
    assert response.status_code == 200
    return response.json()["enrollment_state"]


def test_public_course_detail_returns_trusted_enrollment_cta_state():
    free = published_course(slug="free-course", is_free=True)
    paid = published_course(slug="paid-course", is_free=False)

    guest = APIClient()
    assert state(guest, free) == "FREE_START"
    assert state(guest, paid) == "PAID_REQUEST"

    active_user = User.objects.create_user(email="active@example.com", password="Safe-Pass-2048")
    Enrollment.objects.create(user=active_user, course=paid)
    active_client = APIClient()
    active_client.force_authenticate(active_user)
    assert state(active_client, paid) == "ACTIVE"

    pending_user = User.objects.create_user(email="pending@example.com", password="Safe-Pass-2048")
    EnrollmentRequest.objects.create(user=pending_user, course=paid)
    pending_client = APIClient()
    pending_client.force_authenticate(pending_user)
    assert state(pending_client, paid) == "PENDING"

    rejected_user = User.objects.create_user(
        email="rejected@example.com", password="Safe-Pass-2048"
    )
    EnrollmentRequest.objects.create(
        user=rejected_user,
        course=paid,
        status=EnrollmentRequest.Status.REJECTED,
        reviewed_at=timezone.now(),
    )
    rejected_client = APIClient()
    rejected_client.force_authenticate(rejected_user)
    assert state(rejected_client, paid) == "REJECTED"
