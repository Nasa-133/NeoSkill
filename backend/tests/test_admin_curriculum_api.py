import pytest
from rest_framework.test import APIClient

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
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course(slug: str = "curriculum") -> Course:
    category = Category.objects.create(name=f"Category {slug}", slug=f"category-{slug}")
    instructor = Instructor.objects.create(name=f"Teacher {slug}", slug=f"teacher-{slug}")
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=f"Course {slug}",
        slug=slug,
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
    )


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def admin_client() -> APIClient:
    return client_for(User.objects.create_superuser("curriculum@example.com"))


def test_curriculum_tree_requires_admin():
    parent = course()
    anonymous = APIClient().get(f"/api/v1/admin/courses/{parent.pk}/curriculum")
    assert anonymous.status_code in {401, 403}
    student = User.objects.create_user()
    response = client_for(student).get(f"/api/v1/admin/courses/{parent.pk}/curriculum")
    assert response.status_code == 403


def test_curriculum_tree_returns_lessons_practice_and_test_in_one_call():
    admin = admin_client()
    parent = course()
    module = Module.objects.create(course=parent, title="Module 1", position=1)
    topic = Topic.objects.create(module=module, title="Topic 1", position=1)
    Lesson.objects.create(
        topic=topic,
        title="Lesson 1",
        position=1,
        kind=Lesson.Kind.VIDEO,
        video_url="https://example.com/video",
        duration_minutes=10,
        free_preview=True,
    )
    Practice.objects.create(topic=topic, instructions="Try it")
    TopicTest.objects.create(topic=topic, passing_score=70)

    response = admin.get(f"/api/v1/admin/courses/{parent.pk}/curriculum")

    assert response.status_code == 200
    tree = response.json()
    assert [item["title"] for item in tree] == ["Module 1"]
    first_topic = tree[0]["topics"][0]
    assert first_topic["title"] == "Topic 1"
    assert first_topic["lessons"][0]["free_preview"] is True
    assert first_topic["practice"]["instructions"] == "Try it"
    assert first_topic["test"]["passing_score"] == 70


def test_curriculum_tree_reports_missing_practice_and_test_as_null():
    admin = admin_client()
    parent = course()
    module = Module.objects.create(course=parent, title="Module 1", position=1)
    Topic.objects.create(module=module, title="Empty topic", position=1)

    tree = admin.get(f"/api/v1/admin/courses/{parent.pk}/curriculum").json()
    topic_payload = tree[0]["topics"][0]

    assert topic_payload["lessons"] == []
    assert topic_payload["practice"] is None
    assert topic_payload["test"] is None


def test_unknown_course_curriculum_returns_404():
    admin = admin_client()
    missing = "00000000-0000-4000-8000-000000000000"
    assert admin.get(f"/api/v1/admin/courses/{missing}/curriculum").status_code == 404


def test_admin_lists_can_be_narrowed_to_one_parent():
    admin = admin_client()
    first = course("first")
    second = course("second")
    kept = Module.objects.create(course=first, title="Kept", position=1)
    Module.objects.create(course=second, title="Other", position=1)
    Topic.objects.create(module=kept, title="Kept topic", position=1)

    modules = admin.get(f"/api/v1/admin/modules?course={first.pk}").json()
    assert [item["title"] for item in modules] == ["Kept"]

    topics = admin.get(f"/api/v1/admin/topics?module={kept.pk}").json()
    assert [item["title"] for item in topics] == ["Kept topic"]

    assert len(admin.get("/api/v1/admin/modules").json()) == 2


def test_admin_list_filter_rejects_a_malformed_parent_id():
    admin = admin_client()
    assert admin.get("/api/v1/admin/modules?course=not-a-uuid").status_code == 400
