import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course_lessons() -> tuple[Course, Lesson, Lesson]:
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
    preview = Lesson.objects.create(
        topic=topic,
        title="Preview",
        position=1,
        kind=Lesson.Kind.TEXT,
        content="Public content",
        free_preview=True,
    )
    protected = Lesson.objects.create(
        topic=topic,
        title="Protected",
        position=2,
        kind=Lesson.Kind.TEXT,
        content="Protected content",
    )
    return course, preview, protected


def student_client() -> tuple[User, APIClient]:
    user = User.objects.create_user()
    client = APIClient()
    client.force_authenticate(user=user)
    return user, client


def test_student_without_enrollment_can_open_preview_but_not_protected_content():
    _, preview, protected = course_lessons()
    _, client = student_client()
    public_response = client.get(f"/api/v1/learning/lessons/{preview.pk}")
    protected_response = client.get(f"/api/v1/learning/lessons/{protected.pk}")
    assert public_response.status_code == 200
    assert public_response.json()["content"] == "Public content"
    assert protected_response.status_code == 403
    assert "content" not in protected_response.json()


def test_active_enrollment_grants_protected_content_access():
    course, _, protected = course_lessons()
    user, client = student_client()
    Enrollment.objects.create(user=user, course=course)
    response = client.get(f"/api/v1/learning/lessons/{protected.pk}")
    assert response.status_code == 200
    assert response.json()["content"] == "Protected content"


def test_guest_cannot_use_student_learning_endpoint():
    _, _, protected = course_lessons()
    response = APIClient().get(f"/api/v1/learning/lessons/{protected.pk}")
    assert response.status_code in {401, 403}
    assert "content" not in response.json()
