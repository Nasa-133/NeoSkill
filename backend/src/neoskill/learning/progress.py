from dataclasses import dataclass
from uuid import UUID

from neoskill.assessment.models import TestAttempt
from neoskill.catalog.models import Course
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress, PracticeProgress


@dataclass(frozen=True)
class TopicProgressSnapshot:
    required_units: int
    completed_units: int
    percent: int
    is_complete: bool


@dataclass(frozen=True)
class CourseProgressSnapshot:
    required_units: int
    completed_units: int
    percent: int
    is_complete: bool
    topics: dict[UUID, TopicProgressSnapshot]
    completed_lesson_ids: set[UUID]
    completed_practice_ids: set[UUID]
    passed_test_ids: set[UUID]
    failed_test_ids: set[UUID]


def _percent(completed: int, required: int, *, empty_value: int) -> int:
    if required == 0:
        return empty_value
    return completed * 100 // required


def calculate_course_progress(*, course: Course, user: User) -> CourseProgressSnapshot:
    topics = [topic for module in course.modules.all() for topic in module.topics.all()]
    topic_ids = [topic.pk for topic in topics]
    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            user=user,
            lesson__topic_id__in=topic_ids,
            completed_at__isnull=False,
        ).values_list("lesson_id", flat=True)
    )
    completed_practice_ids = set(
        PracticeProgress.objects.filter(
            user=user,
            practice__topic_id__in=topic_ids,
        ).values_list("practice_id", flat=True)
    )
    passed_test_ids = set(
        TestAttempt.objects.filter(
            user=user,
            test__topic_id__in=topic_ids,
            result=TestAttempt.Result.PASSED,
        ).values_list("test_id", flat=True)
    )
    failed_test_ids = (
        set(
            TestAttempt.objects.filter(
                user=user,
                test__topic_id__in=topic_ids,
                result=TestAttempt.Result.FAILED,
            ).values_list("test_id", flat=True)
        )
        - passed_test_ids
    )

    topic_snapshots: dict[UUID, TopicProgressSnapshot] = {}
    course_required = 0
    course_completed = 0
    for topic in topics:
        required_lessons = [lesson for lesson in topic.lessons.all() if lesson.is_required]
        required = len(required_lessons)
        completed = sum(lesson.pk in completed_lesson_ids for lesson in required_lessons)
        practice = getattr(topic, "practice", None)
        if practice is not None and practice.is_required:
            required += 1
            completed += int(practice.pk in completed_practice_ids)
        topic_test = getattr(topic, "test", None)
        if topic_test is not None and topic_test.is_required:
            required += 1
            completed += int(topic_test.pk in passed_test_ids)
        topic_snapshots[topic.pk] = TopicProgressSnapshot(
            required_units=required,
            completed_units=completed,
            percent=_percent(completed, required, empty_value=100),
            is_complete=completed == required,
        )
        course_required += required
        course_completed += completed

    return CourseProgressSnapshot(
        required_units=course_required,
        completed_units=course_completed,
        percent=_percent(course_completed, course_required, empty_value=0),
        is_complete=course_required > 0 and course_completed == course_required,
        topics=topic_snapshots,
        completed_lesson_ids=completed_lesson_ids,
        completed_practice_ids=completed_practice_ids,
        passed_test_ids=passed_test_ids,
        failed_test_ids=failed_test_ids,
    )
