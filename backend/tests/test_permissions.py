import pytest
from django.db import IntegrityError, transaction
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from neoskill.identity.access import (
    IsAdmin,
    IsAuthenticatedUser,
    IsGuest,
    IsStudent,
    is_admin,
    is_authenticated_user,
    is_guest,
    is_student,
)
from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


class GuestProbe(APIView):
    permission_classes = [IsGuest]

    def get(self, request: Request) -> Response:
        return Response({"role": "guest"})


class StudentProbe(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request) -> Response:
        return Response({"role": "student"})


class AdminProbe(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        return Response({"role": "admin"})


class AuthenticatedProbe(APIView):
    permission_classes = [IsAuthenticatedUser]

    def get(self, request: Request) -> Response:
        return Response({"role": "authenticated"})


def response_status(view: type[APIView], user: User | None = None) -> int:
    request = APIRequestFactory().get("/probe")
    if user is not None:
        force_authenticate(request, user=user)
    return view.as_view()(request).status_code


def test_user_manager_assigns_canonical_roles() -> None:
    student = User.objects.create_user("student-role@example.com")
    admin = User.objects.create_superuser("admin-role@example.com")

    assert student.role == User.Role.STUDENT
    assert student.is_staff is False
    assert admin.role == User.Role.ADMIN
    assert admin.is_staff is True
    assert admin.is_superuser is True


def test_database_rejects_role_and_staff_mismatch() -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            "invalid-admin@example.com",
            role=User.Role.ADMIN,
            is_staff=False,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            "invalid-student@example.com",
            role=User.Role.STUDENT,
            is_staff=True,
        )


def test_guest_student_admin_helpers_are_mutually_exclusive() -> None:
    student = User.objects.create_user("helper-student@example.com")
    admin = User.objects.create_superuser("helper-admin@example.com")

    assert is_guest(None)
    assert not is_authenticated_user(None)
    assert is_student(student)
    assert not is_admin(student)
    assert is_admin(admin)
    assert not is_student(admin)


def test_role_permissions_are_enforced_by_drf_views() -> None:
    student = User.objects.create_user("view-student@example.com")
    admin = User.objects.create_superuser("view-admin@example.com")

    assert response_status(GuestProbe) == 200
    assert response_status(GuestProbe, student) == 403

    assert response_status(StudentProbe) == 403
    assert response_status(StudentProbe, student) == 200
    assert response_status(StudentProbe, admin) == 403

    assert response_status(AdminProbe, student) == 403
    assert response_status(AdminProbe, admin) == 200

    assert response_status(AuthenticatedProbe, student) == 200
    assert response_status(AuthenticatedProbe, admin) == 200


def test_inactive_users_are_denied_even_when_their_role_matches() -> None:
    student = User.objects.create_user("inactive@example.com", is_active=False)
    assert response_status(StudentProbe, student) == 403
    assert response_status(AuthenticatedProbe, student) == 403
