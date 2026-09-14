import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import (
    Category,
    Course,
    CourseFAQ,
    Instructor,
    Lesson,
    Module,
    Topic,
)

pytestmark = pytest.mark.django_db


def course_detail_data(*, status: str = Course.Status.PUBLISHED) -> Course:
    category = Category.objects.create(name="Programming", slug="programming")
    instructor = Instructor.objects.create(
        name="Ali",
        slug="ali",
        title="Engineer",
        bio="Backend engineer",
        social_links=["https://t.me/ali"],
    )
    course = Course.objects.create(
        category=category,
        instructor=instructor,
        title="Python",
        slug="python",
        short_description="Python kursi",
        description="Pythonni amaliy o‘rganing.",
        level=Course.Level.BEGINNER,
        language="uz",
        status=status,
        what_you_will_learn=["Syntax", "Functions", "API"],
        audience=["Students", "Beginners", "Developers"],
        requirements=["Computer"],
    )
    module = Module.objects.create(course=course, title="Basics", position=1)
    topic = Topic.objects.create(module=module, title="Introduction", position=1)
    Lesson.objects.create(
        topic=topic,
        title="Preview",
        position=1,
        kind=Lesson.Kind.VIDEO,
        video_url="https://video.example.com/preview",
        material_url="https://cdn.example.com/preview.pdf",
        free_preview=True,
    )
    Lesson.objects.create(
        topic=topic,
        title="Protected",
        position=2,
        kind=Lesson.Kind.TEXT,
        content="Secret lesson content",
        material_url="https://cdn.example.com/secret.pdf",
    )
    CourseFAQ.objects.create(
        course=course,
        question="Kimlar uchun?",
        answer="Boshlovchilar uchun.",
        position=1,
    )
    return course


def test_guest_gets_all_course_conversion_blocks_and_curriculum_lock_state():
    course_detail_data()
    response = APIClient().get("/api/v1/courses/python")
    assert response.status_code == 200
    body = response.json()
    assert body["what_you_will_learn"] == ["Syntax", "Functions", "API"]
    assert body["audience"] == ["Students", "Beginners", "Developers"]
    assert body["requirements"] == ["Computer"]
    assert body["instructor"]["bio"] == "Backend engineer"
    assert body["faqs"][0]["question"] == "Kimlar uchun?"
    lessons = body["modules"][0]["topics"][0]["lessons"]
    assert [lesson["access"] for lesson in lessons] == ["PREVIEW", "LOCKED"]
    assert all("content" not in lesson for lesson in lessons)
    assert all("video_url" not in lesson for lesson in lessons)
    assert all("material_url" not in lesson for lesson in lessons)
    assert "rating" not in body
    assert "telegram_group_url" not in body


def test_draft_course_detail_is_not_public():
    course_detail_data(status=Course.Status.DRAFT)
    assert APIClient().get("/api/v1/courses/python").status_code == 404
