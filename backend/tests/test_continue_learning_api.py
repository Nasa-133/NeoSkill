import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import CourseProgress

pytestmark = pytest.mark.django_db


def learning_data() -> tuple[User, APIClient, list[Lesson]]:
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
    lessons = [
        Lesson.objects.create(
            topic=topic,
            title=f"Lesson {position}",
            position=position,
            kind=Lesson.Kind.TEXT,
            content=f"Content {position}",
        )
        for position in range(1, 4)
    ]
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client, lessons


def test_continue_returns_current_incomplete_then_next_deterministically():
    user, client, lessons = learning_data()
    url = "/api/v1/learning/courses/python/continue"
    assert client.get(url).json()["lesson"]["id"] == str(lessons[0].pk)

    assert client.get(f"/api/v1/learning/lessons/{lessons[1].pk}").status_code == 200
    assert CourseProgress.objects.get(enrollment__user=user).current_lesson == lessons[1]
    assert client.get(url).json()["lesson"]["id"] == str(lessons[1].pk)

    client.post(f"/api/v1/learning/lessons/{lessons[1].pk}/complete", format="json")
    assert client.get(url).json()["lesson"]["id"] == str(lessons[2].pk)


def test_continue_requires_active_enrollment():
    user, client, _ = learning_data()
    Enrollment.objects.filter(user=user).delete()
    assert client.get("/api/v1/learning/courses/python/continue").status_code == 403
