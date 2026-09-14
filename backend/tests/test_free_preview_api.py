import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Lesson, Module, Topic

pytestmark = pytest.mark.django_db


def lessons(*, course_status: str = Course.Status.PUBLISHED) -> tuple[Lesson, Lesson]:
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
        status=course_status,
    )
    module = Module.objects.create(course=course, title="Module", position=1)
    topic = Topic.objects.create(module=module, title="Topic", position=1)
    preview = Lesson.objects.create(
        topic=topic,
        title="Preview",
        position=1,
        kind=Lesson.Kind.VIDEO,
        video_url="https://video.example.com/preview",
        material_url="https://cdn.example.com/preview.pdf",
        free_preview=True,
    )
    protected = Lesson.objects.create(
        topic=topic,
        title="Protected",
        position=2,
        kind=Lesson.Kind.TEXT,
        content="Protected content",
    )
    return preview, protected


def test_guest_can_open_full_free_preview_content():
    preview, _ = lessons()
    response = APIClient().get(f"/api/v1/lessons/{preview.pk}/preview")
    assert response.status_code == 200
    assert response.json()["video_url"] == "https://video.example.com/preview"
    assert response.json()["material_url"] == "https://cdn.example.com/preview.pdf"
    assert response.json()["course_slug"] == "python"


def test_guest_cannot_open_protected_lesson_through_preview_endpoint():
    _, protected = lessons()
    response = APIClient().get(f"/api/v1/lessons/{protected.pk}/preview")
    assert response.status_code == 404
    assert "content" not in response.json()


def test_preview_of_unpublished_course_is_not_public():
    preview, _ = lessons(course_status=Course.Status.DRAFT)
    assert APIClient().get(f"/api/v1/lessons/{preview.pk}/preview").status_code == 404
