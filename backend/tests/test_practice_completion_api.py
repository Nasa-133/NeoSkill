import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Module, Practice, Topic
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import PracticeProgress

pytestmark = pytest.mark.django_db


def practice_data() -> tuple[Topic, Practice, User, APIClient]:
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
    practice = Practice.objects.create(
        topic=topic,
        instructions="Create a function.",
        example="def example(): ...",
        resource_url="https://docs.example.com/functions",
        is_required=True,
    )
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return topic, practice, user, client


def test_practice_is_shown_and_completion_is_idempotent():
    topic, practice, user, client = practice_data()
    url = f"/api/v1/learning/topics/{topic.pk}/practice"
    shown = client.get(url)
    assert shown.status_code == 200
    assert shown.json()["instructions"] == "Create a function."
    assert shown.json()["is_completed"] is False

    first = client.post(url, format="json")
    second = client.post(url, format="json")
    assert first.status_code == second.status_code == 200
    assert first.json()["completed_now"] is True
    assert second.json()["completed_now"] is False
    assert first.json()["completed_at"] == second.json()["completed_at"]
    assert PracticeProgress.objects.filter(user=user, practice=practice).count() == 1
    assert client.get(url).json()["is_completed"] is True


def test_missing_optional_practice_is_not_fabricated():
    topic, practice, _, client = practice_data()
    practice.delete()
    assert client.get(f"/api/v1/learning/topics/{topic.pk}/practice").status_code == 404


def test_practice_requires_active_enrollment():
    topic, _, user, client = practice_data()
    Enrollment.objects.filter(user=user).delete()
    response = client.post(f"/api/v1/learning/topics/{topic.pk}/practice", format="json")
    assert response.status_code == 403
    assert PracticeProgress.objects.count() == 0
