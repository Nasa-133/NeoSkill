from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

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
    validate_image_reference,
)
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User


class ImageReferenceField(serializers.CharField):
    """A URL or a site-relative path such as /api/v1/media/2026/09/name.png."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 500)
        kwargs.setdefault("allow_blank", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data: Any) -> str:
        value = super().to_internal_value(data)
        try:
            validate_image_reference(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from None
        return value


class CategorySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Name is required.")
        return normalized

    def validate_slug(self, value: str) -> str:
        return value.lower()


class InstructorSerializer(serializers.ModelSerializer[Instructor]):
    photo_url = ImageReferenceField()
    social_links = serializers.ListField(
        child=serializers.URLField(max_length=500),
        max_length=5,
        required=False,
    )

    class Meta:
        model = Instructor
        fields = (
            "id",
            "name",
            "slug",
            "title",
            "photo_url",
            "experience",
            "bio",
            "website_url",
            "social_links",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Name is required.")
        return normalized

    def validate_title(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Title is required.")
        return normalized

    def validate_slug(self, value: str) -> str:
        return value.lower()

    def validate_social_links(self, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class CourseSerializer(serializers.ModelSerializer[Course]):
    image_url = ImageReferenceField()
    what_you_will_learn = serializers.ListField(
        child=serializers.CharField(max_length=240, trim_whitespace=True),
        max_length=10,
        required=False,
    )
    audience = serializers.ListField(
        child=serializers.CharField(max_length=240, trim_whitespace=True),
        max_length=8,
        required=False,
    )
    requirements = serializers.ListField(
        child=serializers.CharField(max_length=240, trim_whitespace=True),
        max_length=10,
        required=False,
    )

    class Meta:
        model = Course
        fields = (
            "id",
            "category",
            "instructor",
            "title",
            "slug",
            "short_description",
            "description",
            "image_url",
            "level",
            "language",
            "duration_minutes",
            "is_free",
            "price",
            "status",
            "sequential_learning",
            "what_you_will_learn",
            "audience",
            "requirements",
            "telegram_group_url",
            "support_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_slug(self, value: str) -> str:
        return value.lower()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance
        is_free = attrs.get("is_free", instance.is_free if instance else True)
        price = attrs.get("price", instance.price if instance else None)
        if is_free and price is not None:
            raise serializers.ValidationError({"price": "Free courses cannot have a price."})
        if not is_free and (price is None or price <= 0):
            raise serializers.ValidationError({"price": "Paid courses require a positive price."})

        status = attrs.get("status", instance.status if instance else Course.Status.DRAFT)
        if status == Course.Status.PUBLISHED:
            outcomes = attrs.get(
                "what_you_will_learn", instance.what_you_will_learn if instance else []
            )
            audience = attrs.get("audience", instance.audience if instance else [])
            requirements = attrs.get("requirements", instance.requirements if instance else [])
            if not 3 <= len(outcomes) <= 10:
                raise serializers.ValidationError(
                    {"what_you_will_learn": "Published courses require 3-10 outcomes."}
                )
            if not 3 <= len(audience) <= 8:
                raise serializers.ValidationError(
                    {"audience": "Published courses require 3-8 audience points."}
                )
            if not requirements:
                raise serializers.ValidationError(
                    {"requirements": "Published courses require at least one requirement."}
                )
        return attrs


class CategorySummarySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        model = Category
        fields = ("name", "slug")


class InstructorSummarySerializer(serializers.ModelSerializer[Instructor]):
    class Meta:
        model = Instructor
        fields = ("name", "slug", "title", "photo_url")


class PublicCategorySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class PublicTestimonialSerializer(serializers.ModelSerializer[Testimonial]):
    name = serializers.CharField(source="author_name")
    profession = serializers.CharField(source="author_title")
    text = serializers.CharField(source="quote")
    active = serializers.BooleanField(source="is_published")

    class Meta:
        model = Testimonial
        fields = ("id", "name", "profession", "text", "active", "position")


class PublicCourseListSerializer(serializers.ModelSerializer[Course]):
    category = CategorySummarySerializer(read_only=True)
    instructor = InstructorSummarySerializer(read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "short_description",
            "image_url",
            "level",
            "language",
            "duration_minutes",
            "is_free",
            "price",
            "category",
            "instructor",
        )


class CourseCatalogFilterSerializer(serializers.Serializer[dict[str, object]]):
    category = serializers.SlugField(max_length=140, required=False)
    level = serializers.ChoiceField(choices=Course.Level.choices, required=False)
    is_free = serializers.BooleanField(required=False)
    search = serializers.CharField(max_length=100, trim_whitespace=True, required=False)
    language = serializers.CharField(max_length=40, trim_whitespace=True, required=False)
    price_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )
    price_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, required=False
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        minimum = attrs.get("price_min")
        maximum = attrs.get("price_max")
        if isinstance(minimum, Decimal) and isinstance(maximum, Decimal) and minimum > maximum:
            raise serializers.ValidationError({"price_max": "Must be at least price_min."})
        return attrs


class PublicLessonSummarySerializer(serializers.ModelSerializer[Lesson]):
    access = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "position",
            "kind",
            "duration_minutes",
            "free_preview",
            "access",
        )

    def get_access(self, obj: Lesson) -> str:
        return "PREVIEW" if obj.free_preview else "LOCKED"


class PublicLessonPreviewSerializer(serializers.ModelSerializer[Lesson]):
    course_slug = serializers.CharField(source="topic.module.course.slug", read_only=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "course_slug",
            "title",
            "kind",
            "content",
            "video_url",
            "material_url",
            "duration_minutes",
            "free_preview",
        )


class PublicTopicSummarySerializer(serializers.ModelSerializer[Topic]):
    lessons = PublicLessonSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Topic
        fields = ("id", "title", "position", "lessons")


class PublicModuleSummarySerializer(serializers.ModelSerializer[Module]):
    topics = PublicTopicSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ("id", "title", "position", "topics")


class PublicCourseFAQSerializer(serializers.ModelSerializer[CourseFAQ]):
    class Meta:
        model = CourseFAQ
        fields = ("id", "question", "answer", "position")


class PublicInstructorSerializer(serializers.ModelSerializer[Instructor]):
    class Meta:
        model = Instructor
        fields = (
            "name",
            "slug",
            "title",
            "photo_url",
            "experience",
            "bio",
            "website_url",
            "social_links",
        )


class PublicCourseDetailSerializer(serializers.ModelSerializer[Course]):
    category = CategorySummarySerializer(read_only=True)
    instructor = PublicInstructorSerializer(read_only=True)
    modules = PublicModuleSummarySerializer(many=True, read_only=True)
    faqs = PublicCourseFAQSerializer(many=True, read_only=True)
    referral_discount_percent = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    enrollment_state = serializers.SerializerMethodField()

    def get_enrollment_state(self, obj: Course) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not isinstance(user, User):
            return "FREE_START" if obj.is_free else "PAID_REQUEST"
        if Enrollment.objects.filter(
            user=user, course=obj, status=Enrollment.Status.ACTIVE
        ).exists():
            return "ACTIVE"
        latest_request = (
            EnrollmentRequest.objects.filter(user=user, course=obj)
            .values_list("status", flat=True)
            .first()
        )
        if latest_request == EnrollmentRequest.Status.PENDING:
            return "PENDING"
        if latest_request == EnrollmentRequest.Status.REJECTED:
            return "REJECTED"
        return "FREE_START" if obj.is_free else "PAID_REQUEST"

    def _discount_percent(self, obj: Course) -> int:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if obj.is_free or not isinstance(user, User) or not user.referred_by_id:
            return 0
        return user.referral_discount_applied

    def get_referral_discount_percent(self, obj: Course) -> int:
        return self._discount_percent(obj)

    def get_discounted_price(self, obj: Course) -> str | None:
        if obj.price is None:
            return None
        percent = self._discount_percent(obj)
        amount = (obj.price * (Decimal(100) - Decimal(percent)) / Decimal(100)).quantize(
            Decimal("0.01")
        )
        return f"{amount:.2f}"

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "short_description",
            "description",
            "image_url",
            "level",
            "language",
            "duration_minutes",
            "is_free",
            "price",
            "enrollment_state",
            "referral_discount_percent",
            "discounted_price",
            "what_you_will_learn",
            "audience",
            "requirements",
            "category",
            "instructor",
            "modules",
            "faqs",
        )


class AppendPositionMixin:
    """
    Creating a child appends it, so the caller never has to guess a free position.

    The next position is resolved in `to_internal_value` on purpose: DRF derives a
    UniqueTogetherValidator from the model's (parent, position) constraint, and that
    validator runs before `validate()` and rejects a missing position outright.
    """

    parent_field = ""

    def to_internal_value(self, data: Any) -> Any:
        attrs = super().to_internal_value(data)  # type: ignore[misc]
        if getattr(self, "instance", None) is None and not attrs.get("position"):
            parent = attrs.get(self.parent_field)
            if parent is not None:
                model = self.Meta.model  # type: ignore[attr-defined]
                last = (
                    model.objects.filter(**{self.parent_field: parent})
                    .order_by("-position")
                    .first()
                )
                attrs["position"] = (last.position if last else 0) + 1
        return attrs


class ModuleSerializer(AppendPositionMixin, serializers.ModelSerializer[Module]):
    position = serializers.IntegerField(min_value=1, required=False)
    parent_field = "course"

    class Meta:
        model = Module
        fields = ("id", "course", "title", "position", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class TopicSerializer(AppendPositionMixin, serializers.ModelSerializer[Topic]):
    position = serializers.IntegerField(min_value=1, required=False)
    parent_field = "module"

    class Meta:
        model = Topic
        fields = ("id", "module", "title", "position", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class LessonSerializer(AppendPositionMixin, serializers.ModelSerializer[Lesson]):
    position = serializers.IntegerField(min_value=1, required=False)
    parent_field = "topic"

    class Meta:
        model = Lesson
        fields = (
            "id",
            "topic",
            "title",
            "position",
            "kind",
            "content",
            "video_url",
            "material_url",
            "duration_minutes",
            "is_required",
            "free_preview",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        instance = self.instance
        kind = attrs.get("kind", instance.kind if instance else None)
        content = attrs.get("content", instance.content if instance else "")
        video_url = attrs.get("video_url", instance.video_url if instance else "")
        if kind == Lesson.Kind.VIDEO and not video_url:
            raise serializers.ValidationError({"video_url": "Video lessons require a video URL."})
        if kind == Lesson.Kind.TEXT and not str(content).strip():
            raise serializers.ValidationError({"content": "Text lessons require content."})
        return attrs


class PracticeSerializer(serializers.ModelSerializer[Practice]):
    class Meta:
        model = Practice
        fields = (
            "id",
            "topic",
            "instructions",
            "example",
            "resource_url",
            "is_required",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TopicTestSerializer(serializers.ModelSerializer[TopicTest]):
    passing_score = serializers.IntegerField(min_value=0, max_value=100)
    question_count = serializers.IntegerField(min_value=1, allow_null=True, required=False)

    class Meta:
        model = TopicTest
        fields = (
            "id",
            "topic",
            "passing_score",
            "question_count",
            "is_required",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CourseFAQSerializer(AppendPositionMixin, serializers.ModelSerializer[CourseFAQ]):
    position = serializers.IntegerField(min_value=1, required=False)
    parent_field = "course"

    class Meta:
        model = CourseFAQ
        fields = ("id", "course", "question", "answer", "position")
        read_only_fields = ("id",)

    def validate_question(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Question is required.")
        return normalized

    def validate_answer(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("Answer is required.")
        return normalized


class TestimonialSerializer(serializers.ModelSerializer[Testimonial]):
    photo_url = ImageReferenceField()

    class Meta:
        model = Testimonial
        fields = (
            "id",
            "author_name",
            "author_title",
            "quote",
            "photo_url",
            "is_published",
            "position",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_author_name(self, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise serializers.ValidationError("Author name is required.")
        return normalized

    def validate_quote(self, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise serializers.ValidationError("Quote is required.")
        return normalized


class ReorderSerializer(serializers.Serializer[dict[str, list[object]]]):
    ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=500)

    def validate_ids(self, value: list[object]) -> list[object]:
        if len(set(value)) != len(value):
            raise serializers.ValidationError("IDs must be unique.")
        return value


class AdminCurriculumTopicSerializer(serializers.ModelSerializer[Topic]):
    """A topic with everything the curriculum editor needs to render one row."""

    lessons = LessonSerializer(many=True, read_only=True)
    practice = serializers.SerializerMethodField()
    test = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ("id", "module", "title", "position", "lessons", "practice", "test")

    def get_practice(self, obj: Topic) -> dict[str, Any] | None:
        practice = getattr(obj, "practice", None)
        return PracticeSerializer(practice).data if practice else None

    def get_test(self, obj: Topic) -> dict[str, Any] | None:
        test = getattr(obj, "test", None)
        return TopicTestSerializer(test).data if test else None


class AdminCurriculumModuleSerializer(serializers.ModelSerializer[Module]):
    topics = AdminCurriculumTopicSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ("id", "course", "title", "position", "topics")
