import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor, Module, Topic
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def course(slug: str = "course") -> Course:
    category = Category.objects.create(name=f"Category {slug}", slug=f"category-{slug}")
    instructor = Instructor.objects.create(name=f"Teacher {slug}", slug=f"teacher-{slug}")
    return Course.objects.create(
        category=category,
        instructor=instructor,
        title=f"Course {slug}",
        slug=slug,
        short_description="Short",
        description="Description",
        level=Course.Level.BEGINNER,
        language="uz",
    )


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_only_admin_can_manage_hierarchy():
    student = User.objects.create_user()
    assert APIClient().get("/api/v1/admin/modules").status_code in {401, 403}
    assert client_for(student).get("/api/v1/admin/modules").status_code == 403
    assert client_for(student).get("/api/v1/admin/topics").status_code == 403


def test_admin_can_create_update_list_and_delete_module_and_topic():
    admin = client_for(User.objects.create_superuser("hierarchy@example.com"))
    parent = course()
    module_response = admin.post(
        "/api/v1/admin/modules",
        {"course": str(parent.pk), "title": "Module 1", "position": 1},
        format="json",
    )
    assert module_response.status_code == 201
    module_id = module_response.json()["id"]
    topic_response = admin.post(
        "/api/v1/admin/topics",
        {"module": module_id, "title": "Topic 1", "position": 1},
        format="json",
    )
    assert topic_response.status_code == 201
    topic_id = topic_response.json()["id"]
    assert (
        admin.patch(
            f"/api/v1/admin/topics/{topic_id}", {"title": "Updated"}, format="json"
        ).status_code
        == 200
    )
    assert admin.get("/api/v1/admin/modules").json()[0]["id"] == module_id
    assert admin.delete(f"/api/v1/admin/modules/{module_id}").status_code == 204
    assert not Topic.objects.filter(pk=topic_id).exists()


def test_module_and_topic_reordering_is_atomic_and_contiguous():
    admin = client_for(User.objects.create_superuser("ordering@example.com"))
    parent = course()
    modules = [
        Module.objects.create(course=parent, title=f"Module {position}", position=position)
        for position in range(1, 4)
    ]
    topics = [
        Topic.objects.create(module=modules[0], title=f"Topic {position}", position=position)
        for position in range(1, 4)
    ]

    module_ids = [str(item.pk) for item in reversed(modules)]
    response = admin.post(
        f"/api/v1/admin/courses/{parent.pk}/modules/reorder",
        {"ids": module_ids},
        format="json",
    )
    assert response.status_code == 204
    assert list(parent.modules.values_list("id", flat=True)) == [
        item.pk for item in reversed(modules)
    ]

    topic_ids = [str(topics[1].pk), str(topics[2].pk), str(topics[0].pk)]
    response = admin.post(
        f"/api/v1/admin/modules/{modules[0].pk}/topics/reorder",
        {"ids": topic_ids},
        format="json",
    )
    assert response.status_code == 204
    assert list(modules[0].topics.values_list("id", flat=True)) == [
        topics[1].pk,
        topics[2].pk,
        topics[0].pk,
    ]


def test_reorder_rejects_duplicates_missing_and_foreign_siblings_without_mutation():
    admin = client_for(User.objects.create_superuser("ordering-invalid@example.com"))
    first_course = course("first")
    second_course = course("second")
    first = Module.objects.create(course=first_course, title="First", position=1)
    second = Module.objects.create(course=first_course, title="Second", position=2)
    foreign = Module.objects.create(course=second_course, title="Foreign", position=1)

    for ids in (
        [str(first.pk), str(first.pk)],
        [str(first.pk)],
        [str(first.pk), str(foreign.pk)],
    ):
        response = admin.post(
            f"/api/v1/admin/courses/{first_course.pk}/modules/reorder",
            {"ids": ids},
            format="json",
        )
        assert response.status_code == 400
    assert list(first_course.modules.values_list("id", "position")) == [
        (first.pk, 1),
        (second.pk, 2),
    ]


def test_hierarchy_requires_existing_parent_and_unique_sibling_position():
    admin = client_for(User.objects.create_superuser("orphan@example.com"))
    parent = course()
    Module.objects.create(course=parent, title="Existing", position=1)
    duplicate = admin.post(
        "/api/v1/admin/modules",
        {"course": str(parent.pk), "title": "Duplicate", "position": 1},
        format="json",
    )
    orphan = admin.post(
        "/api/v1/admin/modules",
        {
            "course": "00000000-0000-4000-8000-000000000000",
            "title": "Orphan",
            "position": 2,
        },
        format="json",
    )
    assert duplicate.status_code == 400
    assert orphan.status_code == 400


def test_creating_children_without_a_position_appends_them():
    admin = client_for(User.objects.create_superuser("append@example.com"))
    parent = course("append")

    # Two modules in a row must not collide on the unique (course, position) pair.
    first = admin.post(
        "/api/v1/admin/modules", {"course": str(parent.pk), "title": "Kirish"}, format="json"
    )
    second = admin.post(
        "/api/v1/admin/modules", {"course": str(parent.pk), "title": "Amaliyot"}, format="json"
    )
    assert first.status_code == 201, first.json()
    assert second.status_code == 201, second.json()
    assert [first.json()["position"], second.json()["position"]] == [1, 2]

    module_id = first.json()["id"]
    topics = [
        admin.post(
            "/api/v1/admin/topics", {"module": module_id, "title": f"Mavzu {index}"}, format="json"
        )
        for index in range(3)
    ]
    assert [item.status_code for item in topics] == [201, 201, 201]
    assert [item.json()["position"] for item in topics] == [1, 2, 3]

    topic_id = topics[0].json()["id"]
    lessons = [
        admin.post(
            "/api/v1/admin/lessons",
            {
                "topic": topic_id,
                "title": f"Dars {index}",
                "kind": "TEXT",
                "content": "Matn",
            },
            format="json",
        )
        for index in range(2)
    ]
    assert [item.status_code for item in lessons] == [201, 201]
    assert [item.json()["position"] for item in lessons] == [1, 2]


def test_an_explicit_position_is_still_honoured():
    admin = client_for(User.objects.create_superuser("explicit@example.com"))
    parent = course("explicit")
    response = admin.post(
        "/api/v1/admin/modules",
        {"course": str(parent.pk), "title": "Beshinchi", "position": 5},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["position"] == 5
