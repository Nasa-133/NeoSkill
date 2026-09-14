from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.catalog.models import Course
from neoskill.enrollment.models import EnrollmentRequest
from neoskill.enrollment.serializers import (
    EnrollmentRequestCreateSerializer,
    EnrollmentRequestQueueFilterSerializer,
    EnrollmentRequestSerializer,
    EnrollmentSerializer,
)
from neoskill.enrollment.services import (
    AlreadyEnrolled,
    CourseIsFree,
    CourseIsNotFree,
    EnrollmentRequestConflict,
    enroll_in_free_course,
    request_paid_enrollment,
    review_enrollment_request,
)
from neoskill.identity.access import IsAdmin, IsStudent, is_admin, is_student


class FreeCourseEnrollmentView(APIView):
    permission_classes = [IsStudent]

    def post(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        try:
            result = enroll_in_free_course(user=request.user, course=course)
        except CourseIsNotFree:
            return Response({"detail": "This course requires an enrollment request."}, status=400)
        body = EnrollmentSerializer(result.enrollment).data
        body["next_path"] = f"/learn/{course.slug}"
        return Response(body, status=201 if result.created else 200)


class PaidEnrollmentRequestView(APIView):
    permission_classes = [IsStudent]

    def post(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(Course, slug=slug, status=Course.Status.PUBLISHED)
        payload = EnrollmentRequestCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        try:
            result = request_paid_enrollment(
                user=request.user,
                course=course,
                note=payload.validated_data["note"],
            )
        except CourseIsFree:
            return Response({"detail": "Free courses do not require approval."}, status=400)
        except AlreadyEnrolled:
            return Response({"detail": "The course is already active."}, status=409)
        body = EnrollmentRequestSerializer(result.request).data
        body["next_path"] = "/my-courses"
        return Response(body, status=201 if result.created else 200)


class AdminEnrollmentRequestListView(ListAPIView[EnrollmentRequest]):
    permission_classes = [IsAdmin]
    serializer_class = EnrollmentRequestSerializer

    def get_queryset(self) -> QuerySet[EnrollmentRequest]:
        filters = EnrollmentRequestQueueFilterSerializer(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        return EnrollmentRequest.objects.filter(
            status=filters.validated_data["status"]
        ).select_related("course", "user", "reviewed_by")


class AdminEnrollmentRequestDetailView(RetrieveAPIView[EnrollmentRequest]):
    permission_classes = [IsAdmin]
    serializer_class = EnrollmentRequestSerializer
    queryset = EnrollmentRequest.objects.select_related("course", "user", "reviewed_by")


class AdminEnrollmentRequestDecisionView(APIView):
    permission_classes = [IsAdmin]
    decision = ""

    def post(self, request: Request, pk: UUID) -> Response:
        if not is_admin(request.user):
            return Response({"detail": "Admin authentication required."}, status=403)
        try:
            result = review_enrollment_request(
                request_id=pk,
                reviewer=request.user,
                decision=self.decision,
            )
        except EnrollmentRequest.DoesNotExist:
            return Response({"detail": "Enrollment request not found."}, status=404)
        except EnrollmentRequestConflict:
            return Response({"detail": "Enrollment request is already finalized."}, status=409)
        return Response(EnrollmentRequestSerializer(result.request).data)
