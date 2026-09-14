import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def entities() -> tuple[Category, Instructor]:
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    return category, instructor


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def course_payload(category: Category, instructor: Instructor) -> dict[str, object]:
    return {
        "category": str(category.pk),
        "instructor": str(instructor.pk),
        "title": "Python asoslari",
        "slug": "PYTHON-ASOSLARI",
        "short_description": "Python dasturlash kursi",
        "description": "Pythonni amaliy misollar bilan o‘rganing.",
        "level": Course.Level.BEGINNER,
        "language": "uz",
        "duration_minutes": 600,
        "is_free": False,
        "price": "250000.00",
        "status": Course.Status.DRAFT,
        "sequential_learning": True,
        "what_you_will_learn": ["Syntax", "Functions", "Modules"],
        "audience": ["Beginners", "Students", "Career changers"],
        "requirements": ["Computer"],
    }


def test_guest_and_student_cannot_manage_courses():
    student = User.objects.create_user()
    assert APIClient().get("/api/v1/admin/courses").status_code in {401, 403}
    assert client_for(student).get("/api/v1/admin/courses").status_code == 403


def test_admin_can_create_list_update_and_delete_course():
    category, instructor = entities()
    admin = User.objects.create_superuser("course-admin@example.com")
    client = client_for(admin)
    created = client.post(
        "/api/v1/admin/courses",
        course_payload(category, instructor),
        format="json",
    )
    assert created.status_code == 201
    course_id = created.json()["id"]
    assert created.json()["slug"] == "python-asoslari"
    assert created.json()["price"] == "250000.00"
    assert client.get("/api/v1/admin/courses").json()[0]["id"] == course_id

    updated = client.patch(
        f"/api/v1/admin/courses/{course_id}",
        {"title": "Professional Python"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Professional Python"
    assert client.delete(f"/api/v1/admin/courses/{course_id}").status_code == 204


@pytest.mark.parametrize(
    "changes",
    [
        {"is_free": True, "price": "1.00"},
        {"is_free": False, "price": None},
        {"category": "00000000-0000-4000-8000-000000000000"},
        {"image_url": "javascript:alert(1)"},
    ],
)
def test_invalid_course_input_is_rejected(changes):
    category, instructor = entities()
    payload = {**course_payload(category, instructor), **changes}
    response = client_for(User.objects.create_superuser("invalid@example.com")).post(
        "/api/v1/admin/courses", payload, format="json"
    )
    assert response.status_code == 400


def test_published_course_requires_complete_conversion_content():
    category, instructor = entities()
    payload = course_payload(category, instructor)
    payload["status"] = Course.Status.PUBLISHED
    payload["what_you_will_learn"] = ["Only one"]
    response = client_for(User.objects.create_superuser("publish@example.com")).post(
        "/api/v1/admin/courses", payload, format="json"
    )
    assert response.status_code == 400
    assert "what_you_will_learn" in response.json()
