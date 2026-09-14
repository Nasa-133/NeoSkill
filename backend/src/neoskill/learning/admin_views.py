from uuid import UUID

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.assessment.models import TestAttempt
from neoskill.catalog.models import Course
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.access import IsAdmin
from neoskill.identity.models import User
from neoskill.learning.admin_serializers import AdminTestAttemptSerializer, AdminUserSerializer
from neoskill.learning.models import CourseProgress
from neoskill.learning.progress import calculate_course_progress


class AdminUserProgressView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request, pk: UUID) -> Response:
        user = get_object_or_404(User, pk=pk)
        enrollments = (
            Enrollment.objects.filter(user=user)
            .select_related("course", "course_progress")
            .prefetch_related(
                "course__modules__topics__lessons",
                "course__modules__topics__practice",
                "course__modules__topics__test",
            )
        )
        enrollment_data = []
        for enrollment in enrollments:
            progress = calculate_course_progress(course=enrollment.course, user=user)
            persisted_completion = None
            try:
                persisted_completion = enrollment.course_progress.completed_at
            except CourseProgress.DoesNotExist:
                pass
            enrollment_data.append(
                {
                    "id": enrollment.pk,
                    "course_id": enrollment.course_id,
                    "course_slug": enrollment.course.slug,
                    "course_title": enrollment.course.title,
                    "status": enrollment.status,
                    "progress": {
                        "required_units": progress.required_units,
                        "completed_units": progress.completed_units,
                        "percent": progress.percent,
                        "is_complete": progress.is_complete,
                        "completed_at": persisted_completion,
                    },
                }
            )
        attempts = TestAttempt.objects.filter(user=user).select_related(
            "test__topic__module__course"
        )
        return Response(
            {
                "user": AdminUserSerializer(user).data,
                "enrollments": enrollment_data,
                "test_attempts": AdminTestAttemptSerializer(attempts, many=True).data,
            }
        )


class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        courses = Course.objects.aggregate(
            total=Count("id"),
            free=Count("id", filter=Q(is_free=True)),
            paid=Count("id", filter=Q(is_free=False)),
        )
        attempts = TestAttempt.objects.aggregate(
            passed=Count("id", filter=Q(result=TestAttempt.Result.PASSED)),
            failed=Count("id", filter=Q(result=TestAttempt.Result.FAILED)),
        )
        return Response(
            {
                "total_users": User.objects.count(),
                "active_enrollments": Enrollment.objects.filter(
                    status=Enrollment.Status.ACTIVE
                ).count(),
                "total_courses": courses["total"],
                "free_courses": courses["free"],
                "paid_courses": courses["paid"],
                "pending_requests": EnrollmentRequest.objects.filter(
                    status=EnrollmentRequest.Status.PENDING
                ).count(),
                "passed_attempts": attempts["passed"],
                "failed_attempts": attempts["failed"],
            }
        )


class AdminEnrollmentStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        access_type = request.query_params.get("type", "ALL").upper()
        if access_type not in {"ALL", "FREE", "PAID"}:
            return Response({"type": ["ALL, FREE yoki PAID qiymatini kiriting."]}, status=400)
        enrollments = Enrollment.objects.select_related("user", "course").order_by(
            "-activated_at", "id"
        )
        if access_type != "ALL":
            enrollments = enrollments.filter(course__is_free=access_type == "FREE")
        if search := request.query_params.get("search", "").strip():
            if len(search) > 100:
                return Response({"search": ["Qidiruv 100 belgidan oshmasin."]}, status=400)
            enrollments = enrollments.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(course__title__icontains=search)
            )
        return Response(
            [
                {
                    "id": item.pk,
                    "user_id": item.user_id,
                    "user_email": item.user.email,
                    "user_name": item.user.full_name,
                    "course_id": item.course_id,
                    "course_slug": item.course.slug,
                    "course_title": item.course.title,
                    "access_type": "FREE" if item.course.is_free else "PAID",
                    "status": item.status,
                    "activated_at": item.activated_at,
                }
                for item in enrollments
            ]
        )


class AdminAttemptStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        result = request.query_params.get("result", "ALL").upper()
        if result not in {"ALL", TestAttempt.Result.PASSED, TestAttempt.Result.FAILED}:
            return Response({"result": ["ALL, PASSED yoki FAILED qiymatini kiriting."]}, status=400)
        attempts = TestAttempt.objects.exclude(
            result=TestAttempt.Result.IN_PROGRESS
        ).select_related("user", "test__topic__module__course")
        if result != "ALL":
            attempts = attempts.filter(result=result)
        if search := request.query_params.get("search", "").strip():
            if len(search) > 100:
                return Response({"search": ["Qidiruv 100 belgidan oshmasin."]}, status=400)
            attempts = attempts.filter(
                Q(user__email__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(test__topic__title__icontains=search)
                | Q(test__topic__module__course__title__icontains=search)
            )
        return Response(
            [
                {
                    "id": item.pk,
                    "user_id": item.user_id,
                    "user_email": item.user.email,
                    "user_name": item.user.full_name,
                    "course_slug": item.test.topic.module.course.slug,
                    "course_title": item.test.topic.module.course.title,
                    "topic_title": item.test.topic.title,
                    "score": item.score,
                    "result": item.result,
                    "completed_at": item.completed_at,
                }
                for item in attempts
            ]
        )
