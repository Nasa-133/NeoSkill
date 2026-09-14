import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.catalog.models import Testimonial as StudentTestimonial

pytestmark = pytest.mark.django_db


def test_public_marketing_lists_only_content_connected_to_published_courses():
    visible_category = Category.objects.create(name="Dasturlash", slug="dasturlash")
    hidden_category = Category.objects.create(name="Qoralama", slug="qoralama")
    visible_instructor = Instructor.objects.create(
        name="Ali Valiyev",
        slug="ali-valiyev",
        title="Backend mentor",
        experience="8 yil",
        bio="Amaliy mentor",
    )
    hidden_instructor = Instructor.objects.create(
        name="Draft Mentor", slug="draft-mentor", title="Mentor"
    )
    Course.objects.create(
        category=visible_category,
        instructor=visible_instructor,
        title="Python",
        slug="python-public",
        short_description="Amaliy Python",
        description="Tavsif",
        level=Course.Level.BEGINNER,
        language="uz",
        status=Course.Status.PUBLISHED,
        what_you_will_learn=["Bir", "Ikki", "Uch"],
        audience=["Bir", "Ikki", "Uch"],
        requirements=["Kompyuter"],
    )
    Course.objects.create(
        category=hidden_category,
        instructor=hidden_instructor,
        title="Draft",
        slug="draft-hidden",
        short_description="Draft",
        description="Draft",
        level=Course.Level.BEGINNER,
        language="uz",
    )

    published = StudentTestimonial.objects.create(
        author_name="Nodira",
        author_title="Talaba",
        quote="Juda foydali.",
        is_published=True,
        position=1,
    )
    StudentTestimonial.objects.create(
        author_name="Hidden",
        quote="Qoralama fikr",
        is_published=False,
        position=2,
    )

    client = APIClient()
    categories = client.get("/api/v1/categories")
    instructors = client.get("/api/v1/instructors")
    testimonials = client.get("/api/v1/testimonials")

    assert categories.status_code == instructors.status_code == testimonials.status_code == 200
    assert categories.json() == [
        {"id": str(visible_category.pk), "name": "Dasturlash", "slug": "dasturlash"}
    ]
    assert instructors.json() == [
        {
            "name": "Ali Valiyev",
            "slug": "ali-valiyev",
            "title": "Backend mentor",
            "photo_url": "",
            "experience": "8 yil",
            "bio": "Amaliy mentor",
            "website_url": "",
            "social_links": [],
        }
    ]
    assert testimonials.json() == [
        {
            "id": str(published.pk),
            "name": "Nodira",
            "profession": "Talaba",
            "text": "Juda foydali.",
            "active": True,
            "position": 1,
        }
    ]
