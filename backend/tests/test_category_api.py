from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_guest_and_student_cannot_access_admin_category_endpoints():
    student = User.objects.create_user()
    assert APIClient().get("/api/v1/admin/categories").status_code in {401, 403}
    assert authenticated_client(student).get("/api/v1/admin/categories").status_code == 403
    assert (
        authenticated_client(student)
        .post("/api/v1/admin/categories", {"name": "Design", "slug": "design"}, format="json")
        .status_code
        == 403
    )


def test_admin_can_create_list_update_and_delete_category():
    admin = User.objects.create_superuser("category-admin@example.com")
    client = authenticated_client(admin)

    created = client.post(
        "/api/v1/admin/categories",
        {"name": "  Web   Development  ", "slug": "WEB-DEV"},
        format="json",
    )
    assert created.status_code == 201
    category_id = created.json()["id"]
    assert created.json()["name"] == "Web Development"
    assert created.json()["slug"] == "web-dev"

    listed = client.get("/api/v1/admin/categories")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [category_id]

    updated = client.patch(
        f"/api/v1/admin/categories/{category_id}",
        {"name": "Backend"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Backend"

    assert client.delete(f"/api/v1/admin/categories/{category_id}").status_code == 204
    assert not Category.objects.filter(pk=category_id).exists()


def test_category_input_is_validated_and_uniqueness_is_safe():
    admin = User.objects.create_superuser("validation-admin@example.com")
    client = authenticated_client(admin)
    Category.objects.create(name="Programming", slug="programming")

    duplicate = client.post(
        "/api/v1/admin/categories",
        {"name": "Programming", "slug": "another"},
        format="json",
    )
    invalid_slug = client.post(
        "/api/v1/admin/categories",
        {"name": "Other", "slug": "not a slug!"},
        format="json",
    )
    assert duplicate.status_code == 400
    assert invalid_slug.status_code == 400


def test_category_used_by_course_cannot_be_deleted():
    admin = User.objects.create_superuser("protected-admin@example.com")
    client = authenticated_client(admin)
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Teacher", slug="teacher", title="Engineer")
    Course.objects.create(
        category=category,
        instructor=instructor,
        title="Python",
        slug="python",
        short_description="Python course",
        description="Course description",
        level=Course.Level.BEGINNER,
        language="uz",
        is_free=False,
        price=Decimal("100000.00"),
    )

    response = client.delete(f"/api/v1/admin/categories/{category.pk}")
    assert response.status_code == 409
    assert Category.objects.filter(pk=category.pk).exists()
