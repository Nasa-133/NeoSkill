from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, connection, transaction
from django.test import override_settings
from django.utils import timezone

from neoskill.assessment.models import Question, QuestionOption
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
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress

pytestmark = pytest.mark.django_db


def create_course(*, slug: str = "course", is_free: bool = True) -> Course:
    category = Category.objects.create(name=f"Category {slug}", slug=f"category-{slug}")
    instructor = Instructor.objects.create(name=f"Instructor {slug}", slug=f"instructor-{slug}")
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=f"Course {slug}",
        slug=slug,
        short_description="Short description",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=is_free,
        price=None if is_free else Decimal("100000.00"),
    )


def create_lesson(course: Course) -> Lesson:
    module = Module.objects.create(course=course, title="Module", position=1)
    topic = Topic.objects.create(module=module, title="Topic", position=1)
    return Lesson.objects.create(
        topic=topic,
        title="Lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Content",
    )


def test_schema_runs_only_on_postgresql() -> None:
    assert connection.vendor == "postgresql"


def test_email_identity_is_normalized_and_unique() -> None:
    first = User.objects.create_user("Learner@EXAMPLE.COM")
    assert first.email == "Learner@example.com"
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("Learner@example.com")


def test_course_price_and_hierarchy_order_are_database_constrained() -> None:
    course = create_course()
    with pytest.raises(IntegrityError), transaction.atomic():
        Course.objects.create(
            category=course.category,
            instructor=course.instructor,
            title="Invalid free course",
            slug="invalid-free",
            short_description="Short",
            description="Description",
            level=Course.Level.BEGINNER,
            language="uz",
            is_free=True,
            price=Decimal("1.00"),
        )

    module = Module.objects.create(course=course, title="One", position=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        Module.objects.create(course=course, title="Duplicate", position=1)
    assert module.course_id == course.id


def test_enrollment_and_pending_request_are_idempotency_ready() -> None:
    user = User.objects.create_user("student@example.com")
    course = create_course(slug="paid", is_free=False)
    Enrollment.objects.create(user=user, course=course)
    with pytest.raises(IntegrityError), transaction.atomic():
        Enrollment.objects.create(user=user, course=course)

    request = EnrollmentRequest.objects.create(user=user, course=course)
    with pytest.raises(IntegrityError), transaction.atomic():
        EnrollmentRequest.objects.create(user=user, course=course)
    request.status = EnrollmentRequest.Status.REJECTED
    request.reviewed_at = timezone.now()
    request.save(update_fields=("status", "reviewed_at"))
    EnrollmentRequest.objects.create(user=user, course=course)


def test_completion_is_persisted_independently_from_video_position() -> None:
    user = User.objects.create_user("progress@example.com")
    lesson = create_lesson(create_course(slug="progress"))
    progress = LessonProgress.objects.create(
        user=user,
        lesson=lesson,
        video_position_seconds=42,
    )
    assert progress.is_completed is False
    progress.completed_at = timezone.now()
    progress.save(update_fields=("completed_at",))
    progress.refresh_from_db()
    assert progress.is_completed is True
    assert progress.video_position_seconds == 42


def test_assessment_schema_limits_options_and_trusted_result_range() -> None:
    course = create_course(slug="assessment")
    lesson = create_lesson(course)
    topic_test = TopicTest.objects.create(topic=lesson.topic, passing_score=70)
    question = Question.objects.create(test=topic_test, text="Question?", position=1)
    QuestionOption.objects.create(question=question, text="Correct", position=1, is_correct=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        QuestionOption.objects.create(
            question=question,
            text="Also correct",
            position=2,
            is_correct=True,
        )

    user = User.objects.create_user("attempt@example.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        Attempt.objects.create(
            user=user,
            test=topic_test,
            score=101,
            result=Attempt.Result.PASSED,
            completed_at=timezone.now(),
        )


def test_development_seed_is_complete_and_idempotent() -> None:
    call_command("seed_dev", verbosity=0)
    call_command("seed_dev", verbosity=0)
    course = Course.objects.get(slug="python-asoslari")
    assert course.modules.count() == 1
    topic = course.modules.get().topics.get()
    assert topic.lessons.count() == 1
    assert topic.test.questions.get().options.count() == 4


@override_settings(NEOSKILL_ENVIRONMENT="production")
def test_development_seed_is_disabled_in_production() -> None:
    with pytest.raises(CommandError, match="disabled in production"):
        call_command("seed_dev", verbosity=0)


def test_readiness_checks_postgresql(client) -> None:
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "neoskill-backend"}
