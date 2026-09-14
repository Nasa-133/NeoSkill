from uuid import UUID

import pytest
from rest_framework.test import APIClient

from neoskill.assessment.models import (
    Question,
)
from neoskill.assessment.models import (
    TestAttempt as Attempt,
)
from neoskill.assessment.models import (
    TestAttemptAnswer as AttemptAnswer,
)
from neoskill.catalog.models import Category, Course, Instructor, Module, Topic, TopicTest
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def setup_test_and_client() -> tuple[TopicTest, APIClient]:
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    course = Course.objects.create(
        category=category,
        instructor=instructor,
        title="Python",
        slug="python",
        short_description="Short",
        description="Description",
        level="BEGINNER",
        language="uz",
    )
    module = Module.objects.create(course=course, title="Module", position=1)
    topic = Topic.objects.create(module=module, title="Topic", position=1)
    topic_test = TopicTest.objects.create(topic=topic, passing_score=70)
    client = APIClient()
    client.force_authenticate(user=User.objects.create_superuser("questions@example.com"))
    return topic_test, client


def payload(topic_test: TopicTest, position: int = 1) -> dict[str, object]:
    return {
        "test": str(topic_test.pk),
        "text": "Python nima?",
        "position": position,
        "options": [
            {"text": "Til", "position": 1, "is_correct": True},
            {"text": "DB", "position": 2, "is_correct": False},
            {"text": "OS", "position": 3, "is_correct": False},
            {"text": "Brauzer", "position": 4, "is_correct": False},
        ],
    }


def test_admin_builds_and_updates_exact_four_option_question():
    topic_test, client = setup_test_and_client()
    created = client.post("/api/v1/admin/questions", payload(topic_test), format="json")
    assert created.status_code == 201
    assert len(created.json()["options"]) == 4
    question_id = created.json()["id"]
    changed = payload(topic_test)
    changed["text"] = "Updated?"
    changed["options"][0]["is_correct"] = False
    changed["options"][1]["is_correct"] = True
    updated = client.put(f"/api/v1/admin/questions/{question_id}", changed, format="json")
    assert updated.status_code == 200
    assert sum(item["is_correct"] for item in updated.json()["options"]) == 1


@pytest.mark.parametrize(
    "options",
    [
        [{"text": "Only", "position": 1, "is_correct": True}],
        [
            {"text": str(number), "position": number, "is_correct": number < 3}
            for number in range(1, 5)
        ],
        [{"text": str(number), "position": 1, "is_correct": number == 1} for number in range(1, 5)],
    ],
)
def test_builder_rejects_invalid_option_sets(options):
    topic_test, client = setup_test_and_client()
    data = payload(topic_test)
    data["options"] = options
    assert client.post("/api/v1/admin/questions", data, format="json").status_code == 400
    assert Question.objects.count() == 0


def test_topic_test_validation_permissions_and_question_order():
    topic_test, client = setup_test_and_client()
    student = APIClient()
    student.force_authenticate(user=User.objects.create_user())
    assert student.get("/api/v1/admin/questions").status_code == 403
    assert (
        client.patch(
            f"/api/v1/admin/topic-tests/{topic_test.pk}",
            {"passing_score": 101},
            format="json",
        ).status_code
        == 400
    )

    first = client.post("/api/v1/admin/questions", payload(topic_test, 1), format="json").json()
    second = client.post("/api/v1/admin/questions", payload(topic_test, 2), format="json").json()
    response = client.post(
        f"/api/v1/admin/topic-tests/{topic_test.pk}/questions/reorder",
        {"ids": [second["id"], first["id"]]},
        format="json",
    )
    assert response.status_code == 204
    assert list(topic_test.questions.values_list("id", flat=True)) == [
        UUID(second["id"]),
        UUID(first["id"]),
    ]


def test_question_with_recorded_answer_is_immutable():
    topic_test, client = setup_test_and_client()
    created = client.post("/api/v1/admin/questions", payload(topic_test), format="json")
    question = Question.objects.get(pk=created.json()["id"])
    attempt = Attempt.objects.create(
        user=User.objects.create_user(),
        test=topic_test,
    )
    AttemptAnswer.objects.create(
        attempt=attempt,
        question=question,
        selected_option=question.options.get(position=1),
    )

    assert (
        client.patch(
            f"/api/v1/admin/questions/{question.pk}",
            {"text": "Changed"},
            format="json",
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/admin/questions/{question.pk}").status_code == 409
    assert Question.objects.filter(pk=question.pk).exists()


def test_questions_can_be_appended_and_reordered_without_position_clashes():
    test, admin = setup_test_and_client()

    created = [
        admin.post(
            "/api/v1/admin/questions",
            {
                "test": str(test.pk),
                "text": f"Savol {index}",
                "options": [
                    {"text": f"A{index}", "position": 1, "is_correct": True},
                    {"text": f"B{index}", "position": 2, "is_correct": False},
                    {"text": f"C{index}", "position": 3, "is_correct": False},
                    {"text": f"D{index}", "position": 4, "is_correct": False},
                ],
            },
            format="json",
        )
        for index in range(3)
    ]
    assert [item.status_code for item in created] == [201, 201, 201], [
        item.json() for item in created
    ]
    assert [item.json()["position"] for item in created] == [1, 2, 3]

    ids = [item.json()["id"] for item in created]
    reversed_ids = list(reversed(ids))
    response = admin.post(
        f"/api/v1/admin/topic-tests/{test.pk}/questions/reorder",
        {"ids": reversed_ids},
        format="json",
    )
    assert response.status_code == 204

    listed = admin.get(f"/api/v1/admin/questions?test={test.pk}").json()
    assert [item["id"] for item in listed] == reversed_ids
    assert [item["position"] for item in listed] == [1, 2, 3]
