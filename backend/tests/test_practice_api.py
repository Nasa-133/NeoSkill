import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Module, Practice, Topic
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def topic() -> Topic:
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
    return Topic.objects.create(module=module, title="Topic", position=1)


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_only_admin_can_manage_practice():
    student = User.objects.create_user()
    assert APIClient().get("/api/v1/admin/practices").status_code in {401, 403}
    assert client_for(student).get("/api/v1/admin/practices").status_code == 403


def test_admin_can_create_update_list_and_delete_optional_practice():
    parent = topic()
    client = client_for(User.objects.create_superuser("practice@example.com"))
    created = client.post(
        "/api/v1/admin/practices",
        {
            "topic": str(parent.pk),
            "instructions": "Funksiya yozing.",
            "example": "def add(a, b): ...",
            "resource_url": "https://docs.python.org/3/",
            "is_required": False,
        },
        format="json",
    )
    assert created.status_code == 201
    practice_id = created.json()["id"]
    assert client.get("/api/v1/admin/practices").json()[0]["id"] == practice_id
    assert (
        client.patch(
            f"/api/v1/admin/practices/{practice_id}", {"is_required": True}, format="json"
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/admin/practices/{practice_id}").status_code == 204


def test_topic_has_at_most_one_practice_and_input_is_validated():
    parent = topic()
    Practice.objects.create(topic=parent, instructions="Existing")
    client = client_for(User.objects.create_superuser("practice-validation@example.com"))
    duplicate = client.post(
        "/api/v1/admin/practices",
        {"topic": str(parent.pk), "instructions": "Duplicate"},
        format="json",
    )
    invalid_url = client.post(
        "/api/v1/admin/practices",
        {
            "topic": str(parent.pk),
            "instructions": "Duplicate",
            "resource_url": "javascript:alert(1)",
        },
        format="json",
    )
    assert duplicate.status_code == 400
    assert invalid_url.status_code == 400
