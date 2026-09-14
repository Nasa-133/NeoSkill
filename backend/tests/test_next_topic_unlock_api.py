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
from neoskill.learning.models import CourseProgress, LessonProgress

pytestmark = pytest.mark.django_db


def unlock_data() -> tuple[TopicTest, Lesson, User, APIClient]:
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
    first_topic = Topic.objects.create(module=module, title="First", position=1)
    second_topic = Topic.objects.create(module=module, title="Second", position=2)
    first_lesson = Lesson.objects.create(
        topic=first_topic,
        title="First lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="First",
    )
    second_lesson = Lesson.objects.create(
        topic=second_topic,
        title="Second lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Second",
    )
    topic_test = TopicTest.objects.create(topic=first_topic, passing_score=70)
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    LessonProgress.objects.create(user=user, lesson=first_lesson, completed_at=timezone.now())
    client = APIClient()
    client.force_authenticate(user=user)
    return topic_test, second_lesson, user, client


def test_fail_keeps_next_topic_locked_pass_unlocks_and_final_topic_completes_course():
    topic_test, second_lesson, user, client = unlock_data()
    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=50,
        result=Attempt.Result.FAILED,
        completed_at=timezone.now(),
    )
    lesson_url = f"/api/v1/learning/lessons/{second_lesson.pk}"
    assert client.get(lesson_url).status_code == 403

    Attempt.objects.create(
        user=user,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    assert client.get(lesson_url).status_code == 200
    completed = client.post(f"{lesson_url}/complete", format="json")
    assert completed.status_code == 200
    progress = CourseProgress.objects.get(enrollment__user=user)
    assert progress.completed_at is not None

    navigation = client.get("/api/v1/learning/courses/python").json()
    topics = navigation["modules"][0]["topics"]
    assert topics[1]["is_locked"] is False
    assert topics[1]["is_completed"] is True
