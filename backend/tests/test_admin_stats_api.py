from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.assessment.models import TestAttempt as Attempt
from neoskill.catalog.models import Category, Course, Instructor, Module, Topic, TopicTest
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def stats_data() -> APIClient:
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    free = Course.objects.create(
        category=category,
        instructor=instructor,
        title="Free",
        slug="free",
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
    )
    paid = Course.objects.create(
        category=category,
        instructor=instructor,
        title="Paid",
        slug="paid",
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=False,
        price=Decimal("100000.00"),
    )
    student = User.objects.create_user()
    Enrollment.objects.create(user=student, course=free)
    EnrollmentRequest.objects.create(user=student, course=paid)
    module = Module.objects.create(course=free, title="Module", position=1)
    topic = Topic.objects.create(module=module, title="Topic", position=1)
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    Attempt.objects.create(
        user=student,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    Attempt.objects.create(
        user=student,
        test=topic_test,
        score=50,
        result=Attempt.Result.FAILED,
        completed_at=timezone.now(),
    )
    admin = User.objects.create_superuser("admin@example.com")
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


def test_admin_gets_basic_product_stats():
    client = stats_data()
    response = client.get("/api/v1/admin/stats")
    assert response.status_code == 200
    assert response.json() == {
        "total_users": 2,
        "active_enrollments": 1,
        "total_courses": 2,
        "free_courses": 1,
        "paid_courses": 1,
        "pending_requests": 1,
        "passed_attempts": 1,
        "failed_attempts": 1,
    }


def test_student_cannot_read_admin_stats():
    client = stats_data()
    student = User.objects.filter(role=User.Role.STUDENT).get()
    client.force_authenticate(user=student)
    assert client.get("/api/v1/admin/stats").status_code == 403


def test_admin_can_open_complete_filtered_enrollment_details():
    client = stats_data()
    free = client.get("/api/v1/admin/statistics/enrollments?type=FREE")
    assert free.status_code == 200
    assert len(free.json()) == 1
    assert free.json()[0]["course_title"] == "Free"
    assert free.json()[0]["access_type"] == "FREE"
    assert client.get("/api/v1/admin/statistics/enrollments?type=PAID").json() == []
    assert len(client.get("/api/v1/admin/statistics/enrollments?search=free").json()) == 1
    assert client.get("/api/v1/admin/statistics/enrollments?type=wrong").status_code == 400


def test_admin_can_open_complete_filtered_attempt_details():
    client = stats_data()
    passed = client.get("/api/v1/admin/statistics/attempts?result=PASSED")
    assert passed.status_code == 200
    assert len(passed.json()) == 1
    assert passed.json()[0]["score"] == 100
    assert passed.json()[0]["course_title"] == "Free"
    failed = client.get("/api/v1/admin/statistics/attempts?result=FAILED&search=topic")
    assert len(failed.json()) == 1
    assert failed.json()[0]["score"] == 50
    assert client.get("/api/v1/admin/statistics/attempts?result=wrong").status_code == 400


def test_students_cannot_open_statistic_details():
    client = stats_data()
    student = User.objects.filter(role=User.Role.STUDENT).get()
    client.force_authenticate(user=student)
    assert client.get("/api/v1/admin/statistics/enrollments").status_code == 403
    assert client.get("/api/v1/admin/statistics/attempts").status_code == 403
