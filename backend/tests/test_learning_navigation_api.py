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


def navigation_data(user: User) -> tuple[Course, Lesson, Lesson, TopicTest]:
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
    first_topic = Topic.objects.create(module=module, title="First topic", position=1)
    second_topic = Topic.objects.create(module=module, title="Second topic", position=2)
    first = Lesson.objects.create(
        topic=first_topic,
        title="First lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="First",
    )
    second = Lesson.objects.create(
        topic=second_topic,
        title="Second lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Second",
    )
    topic_test = TopicTest.objects.create(topic=first_topic, passing_score=70)
    Enrollment.objects.create(user=user, course=course)
    return course, first, second, topic_test


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_navigation_returns_ordered_completion_and_lock_states():
    user = User.objects.create_user()
    _, first, _, topic_test = navigation_data(user)
    LessonProgress.objects.create(user=user, lesson=first, completed_at=timezone.now())
    response = client_for(user).get("/api/v1/learning/courses/python")
    assert response.status_code == 200
    topics = response.json()["modules"][0]["topics"]
    assert topics[0]["lessons"][0]["is_completed"] is True
    assert topics[0]["is_locked"] is False
    assert topics[1]["is_locked"] is True

    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    unlocked = client_for(user).get("/api/v1/learning/courses/python").json()
    assert unlocked["modules"][0]["topics"][1]["is_locked"] is False


def test_navigation_requires_active_enrollment():
    user = User.objects.create_user()
    course, _, _, _ = navigation_data(user)
    Enrollment.objects.filter(user=user, course=course).delete()
    assert client_for(user).get("/api/v1/learning/courses/python").status_code == 403


def test_navigation_exposes_practice_and_test_state_for_the_sidebar():
    user = User.objects.create_user()
    _, first, _, topic_test = navigation_data(user)
    practice = Practice.objects.create(topic=first.topic, instructions="Try it")

    locked = client_for(user).get("/api/v1/learning/courses/python").json()
    first_topic = locked["modules"][0]["topics"][0]
    assert first_topic["practice"] == {
        "id": str(practice.pk),
        "is_required": False,
        "is_completed": False,
    }
    # The required lesson is unfinished, so the test is not offered yet.
    assert first_topic["test"]["status"] == "LOCKED"
    assert first_topic["lessons"][0]["is_required"] is True

    LessonProgress.objects.create(user=user, lesson=first, completed_at=timezone.now())
    PracticeProgress.objects.create(user=user, practice=practice, completed_at=timezone.now())
    ready = client_for(user).get("/api/v1/learning/courses/python").json()
    ready_topic = ready["modules"][0]["topics"][0]
    assert ready_topic["practice"]["is_completed"] is True
    assert ready_topic["test"]["status"] == "READY"

    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=10,
        result=Attempt.Result.FAILED,
        completed_at=timezone.now(),
    )
    failed = client_for(user).get("/api/v1/learning/courses/python").json()
    assert failed["modules"][0]["topics"][0]["test"]["status"] == "FAILED"

    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    passed = client_for(user).get("/api/v1/learning/courses/python").json()
    assert passed["modules"][0]["topics"][0]["test"]["status"] == "PASSED"


def test_navigation_reports_a_topic_without_practice_or_test_as_null():
    user = User.objects.create_user()
    navigation_data(user)
    second_topic = client_for(user).get("/api/v1/learning/courses/python").json()
    payload = second_topic["modules"][0]["topics"][1]
    assert payload["practice"] is None
    assert payload["test"] is None
