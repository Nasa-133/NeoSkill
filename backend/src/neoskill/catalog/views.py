from typing import Any
from uuid import UUID

from django.db.models import Q, QuerySet
from django.db.models.deletion import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from neoskill.catalog.models import (
    Category,
    Course,
    CourseFAQ,
    Instructor,
    Lesson,
    Module,
    Practice,
    Testimonial,
    Topic,
    TopicTest,
)
from neoskill.catalog.ordering import reorder_lessons, reorder_modules, reorder_topics
from neoskill.catalog.serializers import (
    AdminCurriculumModuleSerializer,
    CategorySerializer,
    CourseCatalogFilterSerializer,
    CourseFAQSerializer,
    CourseSerializer,
    InstructorSerializer,
    LessonSerializer,
    ModuleSerializer,
    PracticeSerializer,
    PublicCategorySerializer,
    PublicCourseDetailSerializer,
    PublicCourseListSerializer,
    PublicInstructorSerializer,
    PublicLessonPreviewSerializer,
    PublicTestimonialSerializer,
    ReorderSerializer,
    TestimonialSerializer,
    TopicSerializer,
    TopicTestSerializer,
)
from neoskill.identity.access import IsAdmin


class ParentFilterMixin:
    """Narrows an admin list to one parent, so the editor loads a single course's tree."""

    parent_filters: tuple[str, ...] = ()

    def get_queryset(self) -> QuerySet[Any]:
        queryset: QuerySet[Any] = super().get_queryset()  # type: ignore[misc]
        for field in self.parent_filters:
            raw = self.request.query_params.get(field)  # type: ignore[attr-defined]
            if not raw:
                continue
            try:
                value = UUID(raw)
            except ValueError:
                raise ValidationError({field: "Expected a UUID."}) from None
            queryset = queryset.filter(**{field: value})
        return queryset


class CoursePagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48


class PublicCourseListView(ListAPIView[Course]):
    permission_classes = [AllowAny]
    serializer_class = PublicCourseListSerializer
    pagination_class = CoursePagination

    def get_queryset(self) -> QuerySet[Course]:
        filters = CourseCatalogFilterSerializer(data=self.request.query_params.dict())
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        queryset = Course.objects.filter(status=Course.Status.PUBLISHED).select_related(
            "category", "instructor"
        )
        if category := values.get("category"):
            queryset = queryset.filter(category__slug=category)
        if level := values.get("level"):
            queryset = queryset.filter(level=level)
        if "is_free" in values:
            queryset = queryset.filter(is_free=values["is_free"])
        if search := values.get("search"):
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(short_description__icontains=search)
            )
        if language := values.get("language"):
            queryset = queryset.filter(language__iexact=language)
        if "price_min" in values:
            queryset = queryset.filter(price__gte=values["price_min"])
        if "price_max" in values:
            queryset = queryset.filter(price__lte=values["price_max"])
        return queryset


class PublicCategoryListView(ListAPIView[Category]):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicCategorySerializer
    pagination_class = None
    queryset = Category.objects.filter(courses__status=Course.Status.PUBLISHED).distinct()


class PublicInstructorListView(ListAPIView[Instructor]):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicInstructorSerializer
    pagination_class = None
    queryset = Instructor.objects.filter(courses__status=Course.Status.PUBLISHED).distinct()


class PublicTestimonialListView(ListAPIView[Testimonial]):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicTestimonialSerializer
    pagination_class = None
    queryset = Testimonial.objects.filter(is_published=True)


class PublicCourseDetailView(RetrieveAPIView[Course]):
    permission_classes = [AllowAny]
    serializer_class = PublicCourseDetailSerializer
    lookup_field = "slug"
    queryset = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("category", "instructor")
        .prefetch_related("faqs", "modules__topics__lessons")
    )


class PublicLessonPreviewView(RetrieveAPIView[Lesson]):
    permission_classes = [AllowAny]
    serializer_class = PublicLessonPreviewSerializer
    queryset = Lesson.objects.filter(
        free_preview=True,
        topic__module__course__status=Course.Status.PUBLISHED,
    ).select_related("topic__module__course")


class AdminCategoryViewSet(ModelViewSet[Category]):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Category is used by one or more courses."},
                status=409,
            )


class AdminInstructorViewSet(ModelViewSet[Instructor]):
    queryset = Instructor.objects.all()
    serializer_class = InstructorSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Instructor is used by one or more courses."},
                status=409,
            )


class AdminCourseViewSet(ModelViewSet[Course]):
    queryset = Course.objects.select_related("category", "instructor")
    serializer_class = CourseSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]


class AdminModuleViewSet(ParentFilterMixin, ModelViewSet[Module]):
    queryset = Module.objects.select_related("course")
    serializer_class = ModuleSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("course",)


class AdminTopicViewSet(ParentFilterMixin, ModelViewSet[Topic]):
    queryset = Topic.objects.select_related("module")
    serializer_class = TopicSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("module",)


class AdminLessonViewSet(ParentFilterMixin, ModelViewSet[Lesson]):
    queryset = Lesson.objects.select_related("topic")
    serializer_class = LessonSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("topic",)


class AdminPracticeViewSet(ParentFilterMixin, ModelViewSet[Practice]):
    queryset = Practice.objects.select_related("topic")
    serializer_class = PracticeSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("topic",)


class AdminTopicTestViewSet(ParentFilterMixin, ModelViewSet[TopicTest]):
    queryset = TopicTest.objects.select_related("topic")
    serializer_class = TopicTestSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("topic",)


class AdminCourseFAQViewSet(ParentFilterMixin, ModelViewSet[CourseFAQ]):
    queryset = CourseFAQ.objects.select_related("course")
    serializer_class = CourseFAQSerializer
    permission_classes = [IsAdmin]
    parent_filters = ("course",)


class AdminTestimonialViewSet(ModelViewSet[Testimonial]):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    permission_classes = [IsAdmin]


class AdminCourseCurriculumView(APIView):
    """The whole module/topic/lesson tree in one request, so the editor loads instantly."""

    permission_classes = [IsAdmin]

    def get(self, request: Request, course_id: UUID) -> Response:
        if not Course.objects.filter(pk=course_id).exists():
            return Response({"detail": "Course not found."}, status=404)
        modules = Module.objects.filter(course_id=course_id).prefetch_related(
            "topics__lessons", "topics__practice", "topics__test"
        )
        return Response(AdminCurriculumModuleSerializer(modules, many=True).data)


class AdminReorderView(APIView):
    permission_classes = [IsAdmin]
    target = ""

    def post(self, request: Request, parent_id: UUID) -> Response:
        serializer = ReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            if self.target == "modules":
                reorder_modules(parent_id, serializer.validated_data["ids"])
            elif self.target == "topics":
                reorder_topics(parent_id, serializer.validated_data["ids"])
            else:
                reorder_lessons(parent_id, serializer.validated_data["ids"])
        except ValueError:
            return Response({"detail": "Invalid sibling order."}, status=400)
        return Response(status=204)
