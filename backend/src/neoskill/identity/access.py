from typing import TypeGuard

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from neoskill.identity.models import User


def _active_user(user: object) -> TypeGuard[User]:
    return isinstance(user, User) and user.is_active and user.is_authenticated


def is_guest(user: object) -> bool:
    return not bool(getattr(user, "is_authenticated", False))


def is_student(user: object) -> TypeGuard[User]:
    return _active_user(user) and user.role == User.Role.STUDENT


def is_admin(user: object) -> TypeGuard[User]:
    return _active_user(user) and user.role == User.Role.ADMIN and user.is_staff


def is_authenticated_user(user: object) -> TypeGuard[User]:
    return is_student(user) or is_admin(user)


class IsGuest(BasePermission):
    """Allow only anonymous callers, for authentication entry endpoints."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_guest(request.user)


class IsStudent(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_student(request.user)


class IsAdmin(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_admin(request.user)


class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return is_authenticated_user(request.user)
