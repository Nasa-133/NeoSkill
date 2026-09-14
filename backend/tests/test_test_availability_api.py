import pytest
from django.utils import timezone
from rest_framework.test import APIClient

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


def setup_test_data() -> tuple[Topic, Lesson, Lesson, User, APIClient]:
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
    required = Lesson.objects.create(
        topic=topic,
        title="Required",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Required",
    )
    optional = Lesson.objects.create(
        topic=topic,
        title="Optional",
        position=2,
        kind=Lesson.Kind.TEXT,
        content="Optional",
        is_required=False,
    )
    TopicTest.objects.create(topic=topic, passing_score=70)
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return topic, required, optional, user, client


def test_test_stays_unavailable_until_required_lessons_are_completed():
    topic, required, optional, user, client = setup_test_data()
    url = f"/api/v1/learning/topics/{topic.pk}/test"
    locked = client.get(url)
    assert locked.status_code == 200
    assert locked.json()["available"] is False
    assert locked.json()["required_lessons"] == 1

    LessonProgress.objects.create(user=user, lesson=optional, completed_at=timezone.now())
    assert client.get(url).json()["available"] is False
    LessonProgress.objects.create(user=user, lesson=required, completed_at=timezone.now())
    ready = client.get(url).json()
    assert ready["available"] is True
    assert ready["completed_required_lessons"] == 1


def test_test_status_requires_active_enrollment():
    topic, _, _, user, client = setup_test_data()
    Enrollment.objects.filter(user=user).delete()
    assert client.get(f"/api/v1/learning/topics/{topic.pk}/test").status_code == 403
