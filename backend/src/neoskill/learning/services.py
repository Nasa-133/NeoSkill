from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from neoskill.catalog.models import Course, Lesson, Practice
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import CourseProgress, LessonProgress, PracticeProgress
from neoskill.learning.navigation import build_learning_navigation, course_is_complete


@dataclass(frozen=True)
class LessonCompletionResult:
    progress: LessonProgress
    completed_now: bool


@dataclass(frozen=True)
class PracticeCompletionResult:
    progress: PracticeProgress
    completed_now: bool


@transaction.atomic
def complete_lesson(
    *, user: User, enrollment: Enrollment, lesson: Lesson
) -> LessonCompletionResult:
    now = timezone.now()
    progress, created = LessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson,
        defaults={"completed_at": now},
    )
    completed_now = created
    if progress.completed_at is None:
        progress.completed_at = now
        progress.save(update_fields=("completed_at", "last_viewed_at"))
        completed_now = True
    CourseProgress.objects.update_or_create(
        enrollment=enrollment,
        defaults={"current_lesson": lesson},
    )
    return LessonCompletionResult(progress=progress, completed_now=completed_now)


def record_current_lesson(*, enrollment: Enrollment, lesson: Lesson) -> None:
    CourseProgress.objects.update_or_create(
        enrollment=enrollment,
        defaults={"current_lesson": lesson},
    )


def select_continue_lesson(*, user: User, enrollment: Enrollment, course: Course) -> Lesson | None:
    navigation = build_learning_navigation(course=course, user=user)
    ordered_ids = [
        lesson["id"]
        for module in navigation["modules"]
        for topic in module["topics"]
        for lesson in topic["lessons"]
    ]
    available_incomplete = [
        lesson["id"]
        for module in navigation["modules"]
        for topic in module["topics"]
        for lesson in topic["lessons"]
        if not lesson["is_locked"] and not lesson["is_completed"]
    ]
    if not available_incomplete:
        return None
    progress = CourseProgress.objects.filter(enrollment=enrollment).first()
    current_id = progress.current_lesson_id if progress else None
    if current_id in available_incomplete:
        selected_id = current_id
    elif current_id in ordered_ids:
        current_index = ordered_ids.index(current_id)
        selected_id = next(
            (item for item in available_incomplete if ordered_ids.index(item) > current_index),
            available_incomplete[0],
        )
    else:
        selected_id = available_incomplete[0]
    assert selected_id is not None
    return Lesson.objects.get(pk=selected_id)


@transaction.atomic
def complete_practice(*, user: User, practice: Practice) -> PracticeCompletionResult:
    progress, created = PracticeProgress.objects.get_or_create(
        user=user,
        practice=practice,
        defaults={"completed_at": timezone.now()},
    )
    return PracticeCompletionResult(progress=progress, completed_now=created)


def sync_course_completion(*, user: User, enrollment: Enrollment, course: Course) -> None:
    if not course_is_complete(course=course, user=user):
        return
    progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
    if progress.completed_at is None:
        progress.completed_at = timezone.now()
        progress.save(update_fields=("completed_at", "updated_at"))
