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
    Practice,
    Topic,
    TopicTest,
)
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress, PracticeProgress

pytestmark = pytest.mark.django_db


def progress_data() -> tuple[User, APIClient, Lesson, Lesson, Practice, TopicTest]:
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
    practice = Practice.objects.create(
        topic=topic,
        instructions="Practice",
        is_required=True,
    )
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client, required, optional, practice, topic_test


def test_one_canonical_progress_formula_is_used_in_dashboard_and_learning():
    user, client, required, optional, practice, topic_test = progress_data()

    def dashboard_progress():
        return client.get("/api/v1/me/courses").json()[0]["progress"]

    assert dashboard_progress()["percent"] == 0
    LessonProgress.objects.create(user=user, lesson=optional, completed_at=timezone.now())
    assert dashboard_progress()["percent"] == 0
    LessonProgress.objects.create(user=user, lesson=required, completed_at=timezone.now())
    assert dashboard_progress()["percent"] == 33
    PracticeProgress.objects.create(user=user, practice=practice, completed_at=timezone.now())
    assert dashboard_progress()["percent"] == 66
    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    dashboard = dashboard_progress()
    navigation = client.get("/api/v1/learning/courses/python").json()
    assert dashboard["percent"] == navigation["progress"]["percent"] == 100
    assert dashboard["is_complete"] is True
    assert navigation["modules"][0]["topics"][0]["progress"] == {
        "required_units": 3,
        "completed_units": 3,
        "percent": 100,
    }
