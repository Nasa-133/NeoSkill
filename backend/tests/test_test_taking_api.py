import pytest
from django.utils import timezone
from rest_framework.test import APIClient

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
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User
from neoskill.learning.models import LessonProgress

pytestmark = pytest.mark.django_db


def setup_test_data() -> tuple[Topic, User, APIClient, list[tuple[Question, list[QuestionOption]]]]:
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
    lesson = Lesson.objects.create(
        topic=topic,
        title="Lesson",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Content",
    )
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70, question_count=2)
    questions = []
    for question_position in range(1, 3):
        question = Question.objects.create(
            test=topic_test,
            text=f"Question {question_position}?",
            position=question_position,
        )
        options = [
            QuestionOption.objects.create(
                question=question,
                text=f"Option {option_position}",
                position=option_position,
                is_correct=option_position == 1,
            )
            for option_position in range(1, 5)
        ]
        questions.append((question, options))
    user = User.objects.create_user()
    Enrollment.objects.create(user=user, course=course)
    LessonProgress.objects.create(user=user, lesson=lesson, completed_at=timezone.now())
    client = APIClient()
    client.force_authenticate(user=user)
    return topic, user, client, questions


def answers(
    questions: list[tuple[Question, list[QuestionOption]]], *, second_correct: bool
) -> list[dict[str, str]]:
    return [
        {"question_id": str(questions[0][0].pk), "option_id": str(questions[0][1][0].pk)},
        {
            "question_id": str(questions[1][0].pk),
            "option_id": str(questions[1][1][0 if second_correct else 1].pk),
        },
    ]


def test_ready_test_renders_without_correct_answer_flags():
    topic, _, client, _ = setup_test_data()
    response = client.get(f"/api/v1/learning/topics/{topic.pk}/test")
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 2
    for question in response.json()["questions"]:
        assert len(question["options"]) == 4
        assert all("is_correct" not in option for option in question["options"])


def test_score_and_result_are_computed_and_saved_server_side():
    topic, user, client, questions = setup_test_data()
    url = f"/api/v1/learning/topics/{topic.pk}/test"
    failed = client.post(
        url,
        {"answers": answers(questions, second_correct=False), "score": 100},
        format="json",
    )
    passed = client.post(
        url,
        {"answers": answers(questions, second_correct=True), "score": 0},
        format="json",
    )
    assert failed.status_code == passed.status_code == 201
    assert (failed.json()["score"], failed.json()["result"]) == (50, Attempt.Result.FAILED)
    assert (passed.json()["score"], passed.json()["result"]) == (100, Attempt.Result.PASSED)
    assert list(Attempt.objects.filter(user=user).values_list("score", "result")) == [
        (100, Attempt.Result.PASSED),
        (50, Attempt.Result.FAILED),
    ]


def test_submission_requires_exact_questions_and_valid_options():
    topic, _, client, questions = setup_test_data()
    url = f"/api/v1/learning/topics/{topic.pk}/test"
    missing = client.post(
        url,
        {"answers": answers(questions, second_correct=True)[:1]},
        format="json",
    )
    wrong_question_option = answers(questions, second_correct=True)
    wrong_question_option[0]["option_id"] = str(questions[1][1][0].pk)
    invalid = client.post(url, {"answers": wrong_question_option}, format="json")
    assert missing.status_code == 400
    assert invalid.status_code == 400
    assert Attempt.objects.count() == 0
