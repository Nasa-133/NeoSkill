import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import CourseProgress, LessonProgress

pytestmark = pytest.mark.django_db


def enrolled_course(user: User) -> tuple[Enrollment, Lesson, Lesson]:
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
    first = Lesson.objects.create(
        topic=topic,
        title="First",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="First",
    )
    second = Lesson.objects.create(
        topic=topic,
        title="Second",
        position=2,
        kind=Lesson.Kind.TEXT,
        content="Second",
    )
    enrollment = Enrollment.objects.create(user=user, course=course)
    return enrollment, first, second


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_my_courses_returns_active_published_course_and_progress_summary():
    user = User.objects.create_user()
    enrollment, first, second = enrolled_course(user)
    LessonProgress.objects.create(user=user, lesson=first, completed_at=timezone.now())
    CourseProgress.objects.create(enrollment=enrollment, current_lesson=second)

    response = client_for(user).get("/api/v1/me/courses")
    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["course"]["slug"] == "python"
    assert item["progress"] == {
        "required_units": 2,
        "completed_units": 1,
        "percent": 50,
        "is_complete": False,
        "current_lesson_id": str(second.pk),
    }
    assert "rating" not in item["course"]


def test_my_courses_empty_state_data_is_an_empty_list():
    user = User.objects.create_user()
    assert client_for(user).get("/api/v1/me/courses").json() == []


def test_my_courses_requires_student_authentication():
    assert APIClient().get("/api/v1/me/courses").status_code in {401, 403}
    admin = User.objects.create_superuser("admin@example.com")
    assert client_for(admin).get("/api/v1/me/courses").status_code == 403
