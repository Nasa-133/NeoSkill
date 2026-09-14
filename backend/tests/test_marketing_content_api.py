import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, CourseFAQ, Instructor
from neoskill.catalog.models import Testimonial as StudentTestimonial
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course_and_admin() -> tuple[Course, APIClient]:
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
    client = APIClient()
    client.force_authenticate(user=User.objects.create_superuser("content@example.com"))
    return course, client


def test_admin_manages_course_faqs():
    course, client = course_and_admin()
    created = client.post(
        "/api/v1/admin/course-faqs",
        {
            "course": str(course.pk),
            "question": "  Kurs kimlar uchun? ",
            "answer": " Boshlovchilar uchun. ",
            "position": 1,
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["question"] == "Kurs kimlar uchun?"
    faq_id = created.json()["id"]
    assert (
        client.patch(
            f"/api/v1/admin/course-faqs/{faq_id}",
            {"answer": "Barcha o‘rganuvchilar uchun."},
            format="json",
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/admin/course-faqs/{faq_id}").status_code == 204


def test_faq_parent_position_is_unique_and_text_is_required():
    course, client = course_and_admin()
    CourseFAQ.objects.create(course=course, question="First?", answer="First.", position=1)
    duplicate = client.post(
        "/api/v1/admin/course-faqs",
        {"course": str(course.pk), "question": "Second?", "answer": "Second.", "position": 1},
        format="json",
    )
    blank = client.post(
        "/api/v1/admin/course-faqs",
        {"course": str(course.pk), "question": "   ", "answer": " ", "position": 2},
        format="json",
    )
    assert duplicate.status_code == 400
    assert blank.status_code == 400


def test_admin_manages_publishable_testimonials_without_rating_fields():
    _, client = course_and_admin()
    created = client.post(
        "/api/v1/admin/testimonials",
        {
            "author_name": "  Nodira  ",
            "author_title": "Talaba",
            "quote": " Juda foydali kurs. ",
            "is_published": False,
            "position": 2,
        },
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["author_name"] == "Nodira"
    assert created.json()["quote"] == "Juda foydali kurs."
    assert "rating" not in created.json()
    testimonial_id = created.json()["id"]
    published = client.patch(
        f"/api/v1/admin/testimonials/{testimonial_id}",
        {"is_published": True},
        format="json",
    )
    assert published.status_code == 200
    assert published.json()["is_published"] is True
    assert StudentTestimonial.objects.get(pk=testimonial_id).is_published is True


def test_only_admin_can_access_marketing_content_management():
    course, _ = course_and_admin()
    student = APIClient()
    student.force_authenticate(user=User.objects.create_user())
    assert student.get("/api/v1/admin/course-faqs").status_code == 403
    assert student.get("/api/v1/admin/testimonials").status_code == 403
    assert APIClient().post(
        "/api/v1/admin/course-faqs",
        {"course": str(course.pk), "question": "Q?", "answer": "A", "position": 1},
        format="json",
    ).status_code in {401, 403}
