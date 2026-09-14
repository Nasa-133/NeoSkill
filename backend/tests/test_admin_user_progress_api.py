import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.assessment.models import TestAttempt as Attempt
from neoskill.catalog.models import (
    Category,
    Course,
    Instructor,
    Lesson,
    Module,
    Topic,
    TopicTest,
)
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress

pytestmark = pytest.mark.django_db


def user_progress_data() -> tuple[User, APIClient]:
    student = User.objects.create_user(
        email="progress-student@example.com", first_name="Aziza", last_name="Sobirova"
    )
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    course = Course.objects.create(
        category=category,
        instructor=instructor,
        title="Python",
        slug="python",
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        status=Course.Status.PUBLISHED,
    )
    module = Module.objects.create(course=course, title="Module", position=1)
    topic = Topic.objects.create(module=module, title="Topic", position=1)
    lesson = Lesson.objects.create(
        topic=topic,
        title="Lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Content",
    )
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    Enrollment.objects.create(user=student, course=course)
    LessonProgress.objects.create(user=student, lesson=lesson, completed_at=timezone.now())
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
    return student, client


def test_admin_sees_user_identity_enrollment_progress_and_attempts():
    student, client = user_progress_data()
    users = client.get("/api/v1/admin/users")
    assert users.status_code == 200
    listed_student = next(item for item in users.json() if item["id"] == str(student.pk))
    assert listed_student["email"] == "progress-student@example.com"

    detail = client.get(f"/api/v1/admin/users/{student.pk}/progress")
    assert detail.status_code == 200
    assert detail.json()["enrollments"][0]["course_slug"] == "python"
    assert detail.json()["enrollments"][0]["progress"]["percent"] == 50
    assert detail.json()["test_attempts"][0]["score"] == 50
    assert detail.json()["test_attempts"][0]["result"] == Attempt.Result.FAILED


def test_student_cannot_access_admin_user_progress():
    student, _ = user_progress_data()
    client = APIClient()
    client.force_authenticate(user=student)
    assert client.get("/api/v1/admin/users").status_code == 403
    assert client.get(f"/api/v1/admin/users/{student.pk}/progress").status_code == 403
