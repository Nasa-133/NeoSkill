from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from neoskill.catalog.models import Course
from neoskill.enrollment.models import Enrollment
from neoskill.identity.access import IsAdmin
from neoskill.identity.models import User
from neoskill.identity.serializers import AdminUserSerializer, SetPasswordSerializer


class SelfLockout(APIException):
    """Stops an admin from removing their own access and locking the panel."""

    status_code = 409
    default_detail = "Bu amal sizni tizimdan chiqarib yuboradi."
    default_code = "self_lockout"


class AdminUserViewSet(ModelViewSet[User]):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[User]:
        queryset = super().get_queryset()
        role = self.request.query_params.get("role")
        if role in {User.Role.STUDENT.value, User.Role.ADMIN.value}:
            queryset = queryset.filter(role=role)
        if (active := self.request.query_params.get("is_active")) in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        if search := self.request.query_params.get("search"):
            queryset = queryset.filter(email__icontains=search)
        return queryset

    def perform_destroy(self, instance: User) -> None:
        if instance.pk == getattr(self.request.user, "pk", None):
            raise SelfLockout("O‘z hisobingizni o‘chira olmaysiz.")
        instance.delete()

    def perform_update(self, serializer: BaseSerializer[User]) -> None:
        instance = serializer.instance
        data = dict(serializer.validated_data)
        if instance is not None and instance.pk == getattr(self.request.user, "pk", None):
            if data.get("role", instance.role) != User.Role.ADMIN:
                raise SelfLockout("O‘z rolingizni pasaytira olmaysiz.")
            if data.get("is_active", instance.is_active) is False:
                raise SelfLockout("O‘z hisobingizni bloklay olmaysiz.")
        serializer.save()


class AdminUserPasswordView(APIView):
    permission_classes = [IsAdmin]
    http_method_names = ["post", "options"]

    def post(self, request: Request, pk: UUID) -> Response:
        user = get_object_or_404(User, pk=pk)
        serializer = SetPasswordSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=("password", "updated_at"))
        return Response(status=204)


class AdminUserCourseAccessView(APIView):
    """Grants or removes a course directly, bypassing the paid request queue."""

    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "delete", "options"]

    def get(self, request: Request, pk: UUID) -> Response:
        user = get_object_or_404(User, pk=pk)
        enrollments = Enrollment.objects.filter(user=user).select_related("course")
        return Response(
            [
                {
                    "id": str(item.pk),
                    "course_id": str(item.course_id),
                    "course_title": item.course.title,
                    "status": item.status,
                    "activated_at": item.activated_at,
                }
                for item in enrollments
            ]
        )

    def post(self, request: Request, pk: UUID) -> Response:
        user = get_object_or_404(User, pk=pk)
        course_id = request.data.get("course_id")
        if not course_id:
            return Response({"detail": "course_id majburiy."}, status=400)
        course = Course.objects.filter(pk=course_id).first()
        if course is None:
            return Response({"detail": "Kurs topilmadi."}, status=404)
        _, created = Enrollment.objects.get_or_create(
            user=user, course=course, defaults={"status": Enrollment.Status.ACTIVE}
        )
        return Response(status=201 if created else 200)

    def delete(self, request: Request, pk: UUID) -> Response:
        user = get_object_or_404(User, pk=pk)
        course_id = request.query_params.get("course_id")
        if not course_id:
            return Response({"detail": "course_id majburiy."}, status=400)
        deleted, _ = Enrollment.objects.filter(user=user, course_id=course_id).delete()
        if not deleted:
            return Response({"detail": "Bu kursga ruxsat berilmagan."}, status=404)
        return Response(status=204)
