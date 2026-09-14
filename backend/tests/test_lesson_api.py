import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def setup_topic() -> Topic:
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
    )
    module = Module.objects.create(course=course, title="Module", position=1)
    return Topic.objects.create(module=module, title="Topic", position=1)


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_only_admin_can_manage_lessons():
    student = User.objects.create_user()
    assert APIClient().get("/api/v1/admin/lessons").status_code in {401, 403}
    assert client_for(student).get("/api/v1/admin/lessons").status_code == 403


def test_admin_can_manage_all_lesson_fields():
    topic = setup_topic()
    client = client_for(User.objects.create_superuser("lesson@example.com"))
    created = client.post(
        "/api/v1/admin/lessons",
        {
            "topic": str(topic.pk),
            "title": "Kirish",
            "position": 1,
            "kind": Lesson.Kind.VIDEO,
            "content": "Tavsif",
            "video_url": "https://video.example.com/lesson",
            "material_url": "https://cdn.example.com/material.pdf",
            "duration_minutes": 20,
            "is_required": True,
            "free_preview": True,
        },
        format="json",
    )
    assert created.status_code == 201
    lesson_id = created.json()["id"]
    assert created.json()["material_url"].endswith("material.pdf")
    assert (
        client.patch(
            f"/api/v1/admin/lessons/{lesson_id}", {"free_preview": False}, format="json"
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/admin/lessons/{lesson_id}").status_code == 204


def test_lesson_kind_parent_url_and_position_are_validated():
    topic = setup_topic()
    client = client_for(User.objects.create_superuser("lesson-validation@example.com"))
    Lesson.objects.create(
        topic=topic, title="Existing", position=1, kind=Lesson.Kind.TEXT, content="x"
    )
    for payload in (
        {"topic": str(topic.pk), "title": "Video", "position": 2, "kind": "VIDEO"},
        {"topic": str(topic.pk), "title": "Text", "position": 2, "kind": "TEXT"},
        {
            "topic": str(topic.pk),
            "title": "Duplicate",
            "position": 1,
            "kind": "TEXT",
            "content": "x",
        },
    ):
        assert client.post("/api/v1/admin/lessons", payload, format="json").status_code == 400


def test_lessons_reorder_atomically():
    topic = setup_topic()
    client = client_for(User.objects.create_superuser("lesson-order@example.com"))
    lessons = [
        Lesson.objects.create(
            topic=topic, title=f"Lesson {position}", position=position, kind="TEXT", content="x"
        )
        for position in range(1, 4)
    ]
    response = client.post(
        f"/api/v1/admin/topics/{topic.pk}/lessons/reorder",
        {"ids": [str(item.pk) for item in reversed(lessons)]},
        format="json",
    )
    assert response.status_code == 204
    assert list(topic.lessons.values_list("id", flat=True)) == [
        item.pk for item in reversed(lessons)
    ]
