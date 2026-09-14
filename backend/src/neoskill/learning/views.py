from uuid import UUID

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.catalog.models import Course, Lesson, Practice
from neoskill.enrollment.access import has_active_enrollment
from neoskill.enrollment.models import Enrollment
from neoskill.identity.access import IsStudent, is_student
from neoskill.learning.navigation import build_learning_navigation, topic_is_unlocked
from neoskill.learning.serializers import (
    MyCourseSerializer,
    StudentLessonSerializer,
    StudentPracticeSerializer,
)
from neoskill.learning.services import (
    complete_lesson,
    complete_practice,
    record_current_lesson,
    select_continue_lesson,
    sync_course_completion,
)


class MyCourseListView(ListAPIView[Enrollment]):
    permission_classes = [IsStudent]
    serializer_class = MyCourseSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Enrollment]:
        if not is_student(self.request.user):
            return Enrollment.objects.none()
        return (
            Enrollment.objects.filter(
                user=self.request.user,
                status=Enrollment.Status.ACTIVE,
                course__status=Course.Status.PUBLISHED,
            )
            .select_related("course__category", "course__instructor", "course_progress")
            .prefetch_related(
                "course__modules__topics__lessons",
                "course__modules__topics__practice",
                "course__modules__topics__test",
            )
        )


class StudentLessonDetailView(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request, pk: UUID) -> Response:
        lesson = get_object_or_404(
            Lesson.objects.select_related("topic__module__course"),
            pk=pk,
            topic__module__course__status=Course.Status.PUBLISHED,
        )
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        course = lesson.topic.module.course
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course,
            status=Enrollment.Status.ACTIVE,
        ).first()
        if not lesson.free_preview and enrollment is None:
            return Response({"detail": "An active enrollment is required."}, status=403)
        if (
            not lesson.free_preview
            and enrollment is not None
            and not topic_is_unlocked(course=course, user=request.user, topic_id=lesson.topic_id)
        ):
            return Response({"detail": "This topic is locked."}, status=403)
        if enrollment is not None:
            record_current_lesson(enrollment=enrollment, lesson=lesson)
        return Response(StudentLessonSerializer(lesson).data)


class CourseLearningNavigationView(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(
            Course.objects.filter(status=Course.Status.PUBLISHED).prefetch_related(
                "modules__topics__lessons",
                "modules__topics__practice",
                "modules__topics__test",
            ),
            slug=slug,
        )
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        if not has_active_enrollment(user=request.user, course=course):
            return Response({"detail": "An active enrollment is required."}, status=403)
        return Response(build_learning_navigation(course=course, user=request.user))


class LessonCompletionView(APIView):
    permission_classes = [IsStudent]

    def post(self, request: Request, pk: UUID) -> Response:
        lesson = get_object_or_404(
            Lesson.objects.select_related("topic__module__course"),
            pk=pk,
            topic__module__course__status=Course.Status.PUBLISHED,
        )
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=lesson.topic.module.course,
            status=Enrollment.Status.ACTIVE,
        ).first()
        if enrollment is None:
            return Response({"detail": "An active enrollment is required."}, status=403)
        course = lesson.topic.module.course
        if not topic_is_unlocked(course=course, user=request.user, topic_id=lesson.topic_id):
            return Response({"detail": "This topic is locked."}, status=403)
        result = complete_lesson(user=request.user, enrollment=enrollment, lesson=lesson)
        sync_course_completion(user=request.user, enrollment=enrollment, course=course)
        return Response(
            {
                "lesson_id": result.progress.lesson_id,
                "completed_at": result.progress.completed_at,
                "completed_now": result.completed_now,
            }
        )


class ContinueLearningView(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(
            Course.objects.filter(status=Course.Status.PUBLISHED).prefetch_related(
                "modules__topics__lessons",
                "modules__topics__practice",
                "modules__topics__test",
            ),
            slug=slug,
        )
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course,
            status=Enrollment.Status.ACTIVE,
        ).first()
        if enrollment is None:
            return Response({"detail": "An active enrollment is required."}, status=403)
        lesson = select_continue_lesson(
            user=request.user,
            enrollment=enrollment,
            course=course,
        )
        if lesson is None:
            return Response({"lesson": None, "next_path": f"/learn/{course.slug}"})
        return Response(
            {
                "lesson": {"id": lesson.pk, "title": lesson.title, "kind": lesson.kind},
                "next_path": f"/learn/{course.slug}/lessons/{lesson.pk}",
            }
        )


class TopicPracticeView(APIView):
    permission_classes = [IsStudent]

    def _practice_and_enrollment(
        self, request: Request, pk: UUID
    ) -> tuple[Practice, Enrollment | None]:
        practice = get_object_or_404(
            Practice.objects.select_related("topic__module__course"),
            topic_id=pk,
            topic__module__course__status=Course.Status.PUBLISHED,
        )
        if not is_student(request.user):
            return practice, None
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=practice.topic.module.course,
            status=Enrollment.Status.ACTIVE,
        ).first()
        return practice, enrollment

    def get(self, request: Request, pk: UUID) -> Response:
        practice, enrollment = self._practice_and_enrollment(request, pk)
        if enrollment is None or not is_student(request.user):
            return Response({"detail": "An active enrollment is required."}, status=403)
        course = practice.topic.module.course
        if not topic_is_unlocked(course=course, user=request.user, topic_id=practice.topic_id):
            return Response({"detail": "This topic is locked."}, status=403)
        body = dict(StudentPracticeSerializer(practice).data)
        body["is_completed"] = practice.student_progress.filter(user=request.user).exists()
        return Response(body)

    def post(self, request: Request, pk: UUID) -> Response:
        practice, enrollment = self._practice_and_enrollment(request, pk)
        if enrollment is None or not is_student(request.user):
            return Response({"detail": "An active enrollment is required."}, status=403)
        course = practice.topic.module.course
        if not topic_is_unlocked(course=course, user=request.user, topic_id=practice.topic_id):
            return Response({"detail": "This topic is locked."}, status=403)
        result = complete_practice(user=request.user, practice=practice)
        sync_course_completion(user=request.user, enrollment=enrollment, course=course)
        return Response(
            {
                "practice_id": result.progress.practice_id,
                "completed_at": result.progress.completed_at,
                "completed_now": result.completed_now,
            }
        )
