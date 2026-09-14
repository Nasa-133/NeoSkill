import pytest
from rest_framework.test import APIClient

from neoskill.catalog.models import Category, Course, Instructor
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-Passw0rd!"
DEVICE = "22222222-2222-4222-8222-222222222222"


def admin_client() -> tuple[User, APIClient]:
    admin = User.objects.create_superuser("owner@example.com", PASSWORD)
    client = APIClient()
    client.force_authenticate(user=admin)
    return admin, client


@pytest.mark.parametrize("operation", ["create", "edit", "password"])
def test_admin_password_validation_uses_target_account(operation):
    _, client = admin_client()
    student = User.objects.create_user(email="UniqueLearner92@example.com", password=PASSWORD)
    if operation == "create":
        response = client.post(
            "/api/v1/admin/users",
            {"email": "OtherLearner73@example.com", "password": "OtherLearner73!"},
            format="json",
        )
        assert not User.objects.filter(email="otherlearner73@example.com").exists()
    elif operation == "edit":
        response = client.patch(
            f"/api/v1/admin/users/{student.pk}",
            {"email": "UpdatedLearner81@example.com", "password": "UpdatedLearner81!"},
            format="json",
        )
    else:
        response = client.post(
            f"/api/v1/admin/users/{student.pk}/password",
            {"password": "UniqueLearner92!"},
            format="json",
        )
    assert response.status_code == 400
    assert "password" in response.json()
    student.refresh_from_db()
    assert student.email == "UniqueLearner92@example.com"
    assert student.check_password(PASSWORD)


def a_course(slug: str = "python") -> Course:
    category = Category.objects.create(name=f"Cat {slug}", slug=f"cat-{slug}")
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


def test_only_admins_reach_user_management():
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)
    assert APIClient().get("/api/v1/admin/users").status_code in {401, 403}
    guest = APIClient()
    guest.force_authenticate(user=student)
    assert guest.get("/api/v1/admin/users").status_code == 403


def test_admin_creates_a_user_who_can_then_sign_in():
    _, client = admin_client()
    created = client.post(
        "/api/v1/admin/users",
        {
            "email": "New@Example.com",
            "first_name": "Aziza",
            "last_name": "Sobirova",
            "role": User.Role.STUDENT,
            "is_active": True,
            "password": PASSWORD,
        },
        format="json",
    )

    assert created.status_code == 201
    assert created.json()["email"] == "new@example.com"
    assert created.json()["full_name"] == "Aziza Sobirova"
    assert "password" not in created.json()

    login = APIClient().post(
        "/api/v1/auth/login",
        {"email": "new@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert login.status_code == 200


def test_creating_a_user_without_a_password_is_rejected():
    _, client = admin_client()
    response = client.post("/api/v1/admin/users", {"email": "nopass@example.com"}, format="json")
    assert response.status_code == 400
    assert "password" in response.json()


def test_promoting_a_user_keeps_the_staff_flag_in_step():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)

    response = client.patch(
        f"/api/v1/admin/users/{student.pk}", {"role": User.Role.ADMIN}, format="json"
    )

    assert response.status_code == 200
    student.refresh_from_db()
    assert student.role == User.Role.ADMIN
    assert student.is_staff is True

    client.patch(f"/api/v1/admin/users/{student.pk}", {"role": User.Role.STUDENT}, format="json")
    student.refresh_from_db()
    assert student.is_staff is False
    assert student.is_superuser is False


def test_blocking_a_user_prevents_sign_in():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)

    assert (
        client.patch(
            f"/api/v1/admin/users/{student.pk}", {"is_active": False}, format="json"
        ).status_code
        == 200
    )
    login = APIClient().post(
        "/api/v1/auth/login",
        {"email": "s@example.com", "password": PASSWORD, "device_id": DEVICE},
        format="json",
    )
    assert login.status_code == 400


def test_admin_sets_another_users_password():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)

    response = client.post(
        f"/api/v1/admin/users/{student.pk}/password", {"password": "Reset-By-Adm1n!"}, format="json"
    )

    assert response.status_code == 204
    login = APIClient().post(
        "/api/v1/auth/login",
        {"email": "s@example.com", "password": "Reset-By-Adm1n!", "device_id": DEVICE},
        format="json",
    )
    assert login.status_code == 200


def test_admin_cannot_lock_themselves_out():
    admin, client = admin_client()

    assert (
        client.patch(
            f"/api/v1/admin/users/{admin.pk}", {"role": User.Role.STUDENT}, format="json"
        ).status_code
        == 409
    )
    assert (
        client.patch(
            f"/api/v1/admin/users/{admin.pk}", {"is_active": False}, format="json"
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/admin/users/{admin.pk}").status_code == 409

    admin.refresh_from_db()
    assert admin.role == User.Role.ADMIN
    assert admin.is_active is True


def test_admin_deletes_another_user():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)
    assert client.delete(f"/api/v1/admin/users/{student.pk}").status_code == 204
    assert not User.objects.filter(pk=student.pk).exists()


def test_admin_grants_and_revokes_course_access():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)
    course = a_course()

    granted = client.post(
        f"/api/v1/admin/users/{student.pk}/courses", {"course_id": str(course.pk)}, format="json"
    )
    assert granted.status_code == 201
    assert Enrollment.objects.filter(
        user=student, course=course, status=Enrollment.Status.ACTIVE
    ).exists()

    # Granting twice is harmless.
    assert (
        client.post(
            f"/api/v1/admin/users/{student.pk}/courses",
            {"course_id": str(course.pk)},
            format="json",
        ).status_code
        == 200
    )

    listed = client.get(f"/api/v1/admin/users/{student.pk}/courses").json()
    assert [item["course_title"] for item in listed] == [course.title]

    revoked = client.delete(f"/api/v1/admin/users/{student.pk}/courses?course_id={course.pk}")
    assert revoked.status_code == 204
    assert not Enrollment.objects.filter(user=student, course=course).exists()


def test_course_access_rejects_an_unknown_course():
    _, client = admin_client()
    student = User.objects.create_user(email="s@example.com", password=PASSWORD)
    missing = "00000000-0000-4000-8000-000000000000"
    response = client.post(
        f"/api/v1/admin/users/{student.pk}/courses", {"course_id": missing}, format="json"
    )
    assert response.status_code == 404


def test_user_list_can_be_filtered():
    _, client = admin_client()
    User.objects.create_user(email="active@example.com", password=PASSWORD)
    blocked = User.objects.create_user(email="blocked@example.com", password=PASSWORD)
    blocked.is_active = False
    blocked.save(update_fields=("is_active",))

    students = client.get(f"/api/v1/admin/users?role={User.Role.STUDENT}").json()
    assert {item["email"] for item in students} == {"active@example.com", "blocked@example.com"}

    only_active = client.get("/api/v1/admin/users?is_active=true").json()
    assert "blocked@example.com" not in {item["email"] for item in only_active}

    searched = client.get("/api/v1/admin/users?search=blocked").json()
    assert [item["email"] for item in searched] == ["blocked@example.com"]
