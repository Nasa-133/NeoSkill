from typing import Any
from uuid import UUID

from neoskill.catalog.models import Course, TopicTest
from neoskill.identity.models import User
from neoskill.learning.progress import CourseProgressSnapshot, calculate_course_progress


def _test_status(
    *,
    test: TopicTest,
    unlocked: bool,
    lessons: list[dict[str, Any]],
    progress: CourseProgressSnapshot,
) -> str:
    """READY only once the topic is open and every required lesson is done."""
    if test.pk in progress.passed_test_ids:
        return "PASSED"
    required_done = all(item["is_completed"] for item in lessons if item["is_required"])
    if not unlocked or not required_done:
        return "LOCKED"
    if test.pk in progress.failed_test_ids:
        return "FAILED"
    return "READY"


def build_learning_navigation(*, course: Course, user: User) -> dict[str, Any]:
    progress = calculate_course_progress(course=course, user=user)
    previous_complete = True
    modules: list[dict[str, Any]] = []
    for module in course.modules.all():
        topics: list[dict[str, Any]] = []
        for topic in module.topics.all():
            unlocked = not course.sequential_learning or previous_complete
            lessons = [
                {
                    "id": lesson.pk,
                    "title": lesson.title,
                    "position": lesson.position,
                    "kind": lesson.kind,
                    "duration_minutes": lesson.duration_minutes,
                    "free_preview": lesson.free_preview,
                    "is_required": lesson.is_required,
                    "is_locked": not unlocked,
                    "is_completed": lesson.pk in progress.completed_lesson_ids,
                }
                for lesson in topic.lessons.all()
            ]
            topic_progress = progress.topics[topic.pk]
            complete = topic_progress.is_complete
            practice = getattr(topic, "practice", None)
            topic_test = getattr(topic, "test", None)
            topics.append(
                {
                    "id": topic.pk,
                    "title": topic.title,
                    "position": topic.position,
                    "is_locked": not unlocked,
                    "is_completed": complete,
                    "progress": {
                        "required_units": topic_progress.required_units,
                        "completed_units": topic_progress.completed_units,
                        "percent": topic_progress.percent,
                    },
                    "practice": (
                        {
                            "id": practice.pk,
                            "is_required": practice.is_required,
                            "is_completed": practice.pk in progress.completed_practice_ids,
                        }
                        if practice is not None
                        else None
                    ),
                    "test": (
                        {
                            "id": topic_test.pk,
                            "status": _test_status(
                                test=topic_test,
                                unlocked=unlocked,
                                lessons=lessons,
                                progress=progress,
                            ),
                        }
                        if topic_test is not None
                        else None
                    ),
                    "lessons": lessons,
                }
            )
            previous_complete = complete if course.sequential_learning else True
        modules.append(
            {
                "id": module.pk,
                "title": module.title,
                "position": module.position,
                "topics": topics,
            }
        )
    return {
        "id": course.pk,
        "title": course.title,
        "slug": course.slug,
        "progress": {
            "required_units": progress.required_units,
            "completed_units": progress.completed_units,
            "percent": progress.percent,
            "is_complete": progress.is_complete,
        },
        "modules": modules,
    }


def topic_is_unlocked(*, course: Course, user: User, topic_id: UUID) -> bool:
    navigation = build_learning_navigation(course=course, user=user)
    return any(
        topic["id"] == topic_id and not topic["is_locked"]
        for module in navigation["modules"]
        for topic in module["topics"]
    )


def course_is_complete(*, course: Course, user: User) -> bool:
    return calculate_course_progress(course=course, user=user).is_complete
