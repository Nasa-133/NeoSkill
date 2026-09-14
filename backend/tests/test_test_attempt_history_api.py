import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from neoskill.assessment.models import TestAttempt as Attempt
from neoskill.catalog.models import Category, Course, Instructor, Module, Topic, TopicTest
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def attempt_data() -> tuple[Topic, TopicTest, User, APIClient]:
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
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    client = APIClient()
    client.force_authenticate(user=user)
    return topic, topic_test, user, client


def test_student_sees_own_failed_and_retry_attempt_history():
    topic, topic_test, user, client = attempt_data()
    failed = Attempt.objects.create(
        user=user,
        test=topic_test,
        score=50,
        result=Attempt.Result.FAILED,
        completed_at=timezone.now(),
    )
    passed = Attempt.objects.create(
        user=user,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    other = User.objects.create_user()
    Attempt.objects.create(
        user=other,
        test=topic_test,
        score=0,
        result=Attempt.Result.FAILED,
        completed_at=timezone.now(),
    )

    response = client.get(f"/api/v1/learning/topics/{topic.pk}/test/attempts")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(passed.pk), str(failed.pk)]
    assert [(item["score"], item["result"]) for item in response.json()] == [
        (100, Attempt.Result.PASSED),
        (50, Attempt.Result.FAILED),
    ]
    assert all("answers" not in item for item in response.json())


def test_attempt_history_requires_active_enrollment():
    topic, _, user, client = attempt_data()
    Enrollment.objects.filter(user=user).delete()
    response = client.get(f"/api/v1/learning/topics/{topic.pk}/test/attempts")
    assert response.status_code == 403
