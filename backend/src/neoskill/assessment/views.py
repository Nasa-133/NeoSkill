from uuid import UUID

from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from neoskill.assessment.models import Question, TestAttempt
from neoskill.assessment.ordering import reorder_questions
from neoskill.assessment.serializers import (
    QuestionSerializer,
    StudentQuestionSerializer,
    TestAttemptListSerializer,
    TestSubmissionSerializer,
)
from neoskill.assessment.services import (
    InvalidTestAnswers,
    TestHasNoQuestions,
    get_test_availability,
    selected_test_questions,
    submit_test_attempt,
)
from neoskill.catalog.models import Course, TopicTest
from neoskill.catalog.serializers import ReorderSerializer
from neoskill.catalog.views import ParentFilterMixin
from neoskill.enrollment.access import has_active_enrollment
from neoskill.enrollment.models import Enrollment
from neoskill.identity.access import IsAdmin, IsStudent, is_student
from neoskill.learning.navigation import topic_is_unlocked
from neoskill.learning.services import sync_course_completion


class QuestionHasAttempts(APIException):
    status_code = 409
    default_detail = "Questions with recorded answers cannot be changed or deleted."
    default_code = "question_has_attempts"


class AdminQuestionViewSet(ParentFilterMixin, ModelViewSet[Question]):
    queryset = Question.objects.select_related("test").prefetch_related("options")
    serializer_class = QuestionSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("test",)

    def perform_update(self, serializer: BaseSerializer[Question]) -> None:
        instance = serializer.instance
        assert instance is not None
        if instance.attempt_answers.exists():
            raise QuestionHasAttempts
        serializer.save()

    def perform_destroy(self, instance: Question) -> None:
        if instance.attempt_answers.exists():
            raise QuestionHasAttempts
        instance.delete()


class AdminQuestionReorderView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request, test_id: UUID) -> Response:
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reorder_questions(test_id, serializer.validated_data["ids"])
        except ValueError:
            return Response({"detail": "Invalid question order."}, status=400)
        return Response(status=204)


class StudentTopicTestStatusView(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request, topic_id: UUID) -> Response:
        try:
            topic_test = TopicTest.objects.select_related("topic__module__course").get(
                topic_id=topic_id,
                topic__module__course__status=Course.Status.PUBLISHED,
            )
        except TopicTest.DoesNotExist:
            return Response({"detail": "Topic test not found."}, status=404)
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        course = topic_test.topic.module.course
        enrollment = Enrollment.objects.filter(
            user=request.user, course=course, status=Enrollment.Status.ACTIVE
        ).first()
        if enrollment is None:
            return Response({"detail": "An active enrollment is required."}, status=403)
        if not topic_is_unlocked(course=course, user=request.user, topic_id=topic_test.topic_id):
            return Response({"detail": "This topic is locked."}, status=403)
        availability = get_test_availability(user=request.user, topic_test=topic_test)
        questions = (
            StudentQuestionSerializer(selected_test_questions(topic_test), many=True).data
            if availability.available
            else []
        )
        return Response(
            {
                "test_id": topic_test.pk,
                "available": availability.available,
                "required_lessons": availability.required_lessons,
                "completed_required_lessons": availability.completed_required_lessons,
                "passing_score": topic_test.passing_score,
                "questions": questions,
            }
        )

    def post(self, request: Request, topic_id: UUID) -> Response:
        try:
            topic_test = TopicTest.objects.select_related("topic__module__course").get(
                topic_id=topic_id,
                topic__module__course__status=Course.Status.PUBLISHED,
            )
        except TopicTest.DoesNotExist:
            return Response({"detail": "Topic test not found."}, status=404)
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        course = topic_test.topic.module.course
        enrollment = Enrollment.objects.filter(
            user=request.user, course=course, status=Enrollment.Status.ACTIVE
        ).first()
        if enrollment is None:
            return Response({"detail": "An active enrollment is required."}, status=403)
        if not topic_is_unlocked(course=course, user=request.user, topic_id=topic_test.topic_id):
            return Response({"detail": "This topic is locked."}, status=403)
        availability = get_test_availability(user=request.user, topic_test=topic_test)
        if not availability.available:
            return Response({"detail": "Required lessons are incomplete."}, status=403)
        payload = TestSubmissionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            attempt = submit_test_attempt(
                user=request.user,
                topic_test=topic_test,
                answers=payload.validated_data["answers"],
            )
        except InvalidTestAnswers:
            return Response({"detail": "Answers do not match this test."}, status=400)
        except TestHasNoQuestions:
            return Response({"detail": "The test has no configured questions."}, status=409)
        sync_course_completion(user=request.user, enrollment=enrollment, course=course)
        return Response(
            {
                "attempt_id": attempt.pk,
                "score": attempt.score,
                "result": attempt.result,
                "completed_at": attempt.completed_at,
            },
            status=201,
        )


class StudentTopicTestAttemptListView(APIView):
    permission_classes = [IsStudent]

    def get(self, request: Request, topic_id: UUID) -> Response:
        try:
            topic_test = TopicTest.objects.select_related("topic__module__course").get(
                topic_id=topic_id,
                topic__module__course__status=Course.Status.PUBLISHED,
            )
        except TopicTest.DoesNotExist:
            return Response({"detail": "Topic test not found."}, status=404)
        if not is_student(request.user):
            return Response({"detail": "Student authentication required."}, status=403)
        if not has_active_enrollment(
            user=request.user,
            course=topic_test.topic.module.course,
        ):
            return Response({"detail": "An active enrollment is required."}, status=403)
        attempts = TestAttempt.objects.filter(user=request.user, test=topic_test)
        return Response(TestAttemptListSerializer(attempts, many=True).data)
