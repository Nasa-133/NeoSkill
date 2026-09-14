import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import CourseProgress, LessonProgress

pytestmark = pytest.mark.django_db


def lesson_and_user() -> tuple[Lesson, User, APIClient]:
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
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return lesson, user, client


def test_lesson_completion_persists_and_is_idempotent():
    lesson, user, client = lesson_and_user()
    url = f"/api/v1/learning/lessons/{lesson.pk}/complete"
    first = client.post(url, format="json")
    second = client.post(url, format="json")
    assert first.status_code == second.status_code == 200
    assert first.json()["completed_now"] is True
    assert second.json()["completed_now"] is False
    assert first.json()["completed_at"] == second.json()["completed_at"]
    progress = LessonProgress.objects.get(user=user, lesson=lesson)
    assert progress.completed_at is not None
    assert CourseProgress.objects.get(enrollment__user=user).current_lesson == lesson

    reloaded = client.get("/api/v1/learning/courses/python").json()
    assert reloaded["modules"][0]["topics"][0]["lessons"][0]["is_completed"] is True


def test_completion_requires_active_enrollment():
    lesson, user, client = lesson_and_user()
    Enrollment.objects.filter(user=user).delete()
    response = client.post(f"/api/v1/learning/lessons/{lesson.pk}/complete", format="json")
    assert response.status_code == 403
    assert LessonProgress.objects.count() == 0
