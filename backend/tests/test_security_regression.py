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

pytestmark = pytest.mark.django_db


def course_content(
    *, slug: str, category: Category, instructor: Instructor
) -> tuple[Course, Topic, Lesson, Practice, TopicTest]:
    course = Course.objects.create(
        category=category,
        instructor=instructor,
        title=slug.title(),
        slug=slug,
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
        title="Protected",
        position=1,
        kind=Lesson.Kind.TEXT,
        content=f"secret-{slug}",
    )
    practice = Practice.objects.create(topic=topic, instructions=f"practice-{slug}")
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    return course, topic, lesson, practice, topic_test


def test_cross_course_enrollment_never_grants_protected_content():
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    allowed, _, allowed_lesson, _, _ = course_content(
        slug="allowed", category=category, instructor=instructor
    )
    _, denied_topic, denied_lesson, _, _ = course_content(
        slug="denied", category=category, instructor=instructor
    )
    student = User.objects.create_user()
    Enrollment.objects.create(user=student, course=allowed)
    client = APIClient()
    client.force_authenticate(user=student)

    assert client.get(f"/api/v1/learning/lessons/{allowed_lesson.pk}").status_code == 200
    denied = client.get(f"/api/v1/learning/lessons/{denied_lesson.pk}")
    assert denied.status_code == 403
    assert "secret-denied" not in denied.content.decode()
    assert client.get(f"/api/v1/learning/topics/{denied_topic.pk}/practice").status_code == 403
    assert client.get(f"/api/v1/learning/topics/{denied_topic.pk}/test").status_code == 403


def test_attempt_history_is_owner_scoped_and_admin_routes_reject_students():
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    course, topic, _, _, topic_test = course_content(
        slug="python", category=category, instructor=instructor
    )
    owner = User.objects.create_user()
    attacker = User.objects.create_user()
    Enrollment.objects.create(user=owner, course=course)
    Enrollment.objects.create(user=attacker, course=course)
    Attempt.objects.create(
        user=owner,
        test=topic_test,
        score=100,
        result=Attempt.Result.PASSED,
        completed_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(user=attacker)
    assert client.get(f"/api/v1/learning/topics/{topic.pk}/test/attempts").json() == []
    assert client.get("/api/v1/admin/stats").status_code == 403
    assert client.get(f"/api/v1/admin/users/{owner.pk}/progress").status_code == 403


def test_public_and_identity_contracts_do_not_expose_secrets_or_password_login():
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    _, _, lesson, _, _ = course_content(slug="python", category=category, instructor=instructor)
    public = APIClient().get("/api/v1/courses/python")
    assert public.status_code == 200
    serialized = public.content.decode()
    assert "secret-python" not in serialized
    assert "is_correct" not in serialized
    assert "password" not in serialized
    assert APIClient().get(f"/api/v1/learning/lessons/{lesson.pk}").status_code in {401, 403}
    user = User.objects.create_user()
    assert user.has_usable_password() is False
