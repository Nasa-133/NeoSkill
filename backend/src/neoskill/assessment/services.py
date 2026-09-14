from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from neoskill.assessment.models import Question, TestAttempt, TestAttemptAnswer
from neoskill.catalog.models import TopicTest
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress


@dataclass(frozen=True)
class TestAvailability:
    available: bool
    required_lessons: int
    completed_required_lessons: int


class InvalidTestAnswers(ValueError):
    pass


class TestHasNoQuestions(ValueError):
    pass


def get_test_availability(*, user: User, topic_test: TopicTest) -> TestAvailability:
    required_lessons = topic_test.topic.lessons.filter(is_required=True)
    required_count = required_lessons.count()
    completed_count = LessonProgress.objects.filter(
        user=user,
        lesson__in=required_lessons,
        completed_at__isnull=False,
    ).count()
    return TestAvailability(
        available=completed_count == required_count,
        required_lessons=required_count,
        completed_required_lessons=completed_count,
    )


def selected_test_questions(topic_test: TopicTest) -> list[Question]:
    limit = topic_test.question_count
    queryset = topic_test.questions.prefetch_related("options").order_by("position", "id")
    return list(queryset[:limit] if limit is not None else queryset)


@transaction.atomic
def submit_test_attempt(
    *, user: User, topic_test: TopicTest, answers: list[dict[str, Any]]
) -> TestAttempt:
    questions = selected_test_questions(topic_test)
    if not questions:
        raise TestHasNoQuestions
    answers_by_question = {answer["question_id"]: answer["option_id"] for answer in answers}
    expected_question_ids = {question.pk for question in questions}
    if set(answers_by_question) != expected_question_ids:
        raise InvalidTestAnswers

    selected_options = []
    correct = 0
    for question in questions:
        option_id = answers_by_question[question.pk]
        option = next((item for item in question.options.all() if item.pk == option_id), None)
        if option is None:
            raise InvalidTestAnswers
        selected_options.append((question, option))
        correct += int(option.is_correct)

    score = correct * 100 // len(questions)
    result = (
        TestAttempt.Result.PASSED
        if score >= topic_test.passing_score
        else TestAttempt.Result.FAILED
    )
    attempt = TestAttempt.objects.create(
        user=user,
        test=topic_test,
        score=score,
        result=result,
        completed_at=timezone.now(),
    )
    TestAttemptAnswer.objects.bulk_create(
        [
            TestAttemptAnswer(
                attempt=attempt,
                question=question,
                selected_option=option,
            )
            for question, option in selected_options
        ]
    )
    return attempt
