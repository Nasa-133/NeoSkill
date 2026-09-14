from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor

pytestmark = pytest.mark.django_db


def create_course(
    *,
    title: str,
    slug: str,
    category: Category,
    instructor: Instructor,
    status: str = Course.Status.PUBLISHED,
    level: str = Course.Level.BEGINNER,
    is_free: bool = True,
) -> Course:
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=title,
        slug=slug,
        short_description=f"{title} haqida",
        description="Description",
        image_url="https://cdn.example.com/course.jpg",
        level=level,
        language="uz",
        duration_minutes=120,
        is_free=is_free,
        price=None if is_free else Decimal("150000.00"),
        status=status,
    )


def catalog_data() -> None:
    programming = Category.objects.create(name="Programming", slug="programming")
    design = Category.objects.create(name="Design", slug="design")
    instructor = Instructor.objects.create(name="Ali", slug="ali", title="Engineer")
    create_course(title="Python", slug="python", category=programming, instructor=instructor)
    create_course(
        title="Advanced Django",
        slug="django",
        category=programming,
        instructor=instructor,
        level=Course.Level.ADVANCED,
        is_free=False,
    )
    create_course(
        title="Hidden Draft",
        slug="hidden",
        category=design,
        instructor=instructor,
        status=Course.Status.DRAFT,
    )


def test_guest_sees_only_published_courses_with_real_metadata_and_no_rating():
    catalog_data()
    response = APIClient().get("/api/v1/courses")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert {course["slug"] for course in body["results"]} == {"python", "django"}
    python = next(course for course in body["results"] if course["slug"] == "python")
    assert python["category"] == {"name": "Programming", "slug": "programming"}
    assert python["instructor"]["name"] == "Ali"
    assert python["duration_minutes"] == 120
    assert "rating" not in python


def test_catalog_filters_by_category_level_price_and_search():
    catalog_data()
    client = APIClient()
    filtered = client.get(
        "/api/v1/courses",
        {"category": "programming", "level": "ADVANCED", "is_free": "false"},
    )
    assert filtered.status_code == 200
    assert [course["slug"] for course in filtered.json()["results"]] == ["django"]
    searched = client.get("/api/v1/courses", {"search": "python"})
    assert [course["slug"] for course in searched.json()["results"]] == ["python"]
    priced = client.get(
        "/api/v1/courses",
        {"language": "UZ", "price_min": "100000", "price_max": "200000"},
    )
    assert [course["slug"] for course in priced.json()["results"]] == ["django"]


@pytest.mark.parametrize(
    "query",
    [
        {"level": "EXPERT"},
        {"is_free": "perhaps"},
        {"category": "not a slug!"},
        {"search": "x" * 101},
        {"price_min": "200000", "price_max": "100000"},
    ],
)
def test_catalog_rejects_invalid_filters(query):
    catalog_data()
    assert APIClient().get("/api/v1/courses", query).status_code == 400
