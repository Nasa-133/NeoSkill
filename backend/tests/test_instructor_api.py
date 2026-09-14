from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def admin_client() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=User.objects.create_superuser("instructor-admin@example.com"))
    return client


def test_guest_and_student_cannot_manage_instructors():
    student = User.objects.create_user()
    student_client = APIClient()
    student_client.force_authenticate(user=student)
    assert APIClient().get("/api/v1/admin/instructors").status_code in {401, 403}
    assert student_client.get("/api/v1/admin/instructors").status_code == 403


def test_admin_can_create_list_update_and_delete_instructor():
    client = admin_client()
    created = client.post(
        "/api/v1/admin/instructors",
        {
            "name": "  Ali   Valiyev ",
            "slug": "ALI-VALIYEV",
            "title": " Senior   Python Engineer ",
            "photo_url": "https://cdn.example.com/ali.jpg",
            "experience": "8 yil tajriba",
            "bio": "Backend mutaxassisi.",
            "website_url": "https://example.com",
            "social_links": [
                "https://t.me/alivaliyev",
                "https://linkedin.com/in/alivaliyev",
                "https://t.me/alivaliyev",
            ],
        },
        format="json",
    )
    assert created.status_code == 201
    instructor_id = created.json()["id"]
    assert created.json()["name"] == "Ali Valiyev"
    assert created.json()["title"] == "Senior Python Engineer"
    assert created.json()["slug"] == "ali-valiyev"
    assert len(created.json()["social_links"]) == 2
    assert client.get("/api/v1/admin/instructors").json()[0]["id"] == instructor_id

    updated = client.patch(
        f"/api/v1/admin/instructors/{instructor_id}",
        {"title": "Lead Engineer"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Lead Engineer"
    assert client.delete(f"/api/v1/admin/instructors/{instructor_id}").status_code == 204


def test_instructor_input_is_validated():
    response = admin_client().post(
        "/api/v1/admin/instructors",
        {
            "name": "   ",
            "slug": "invalid",
            "title": "Engineer",
            "photo_url": "javascript:alert(1)",
            "social_links": ["not-a-url"],
        },
        format="json",
    )
    assert response.status_code == 400


def test_instructor_used_by_course_cannot_be_deleted():
    client = admin_client()
    category = Category.objects.create(name="Backend", slug="backend")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    Course.objects.create(
        category=category,
        instructor=instructor,
        title="Django",
        slug="django",
        short_description="Django course",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=False,
        price=Decimal("100000.00"),
    )
    response = client.delete(f"/api/v1/admin/instructors/{instructor.pk}")
    assert response.status_code == 409
    assert Instructor.objects.filter(pk=instructor.pk).exists()
