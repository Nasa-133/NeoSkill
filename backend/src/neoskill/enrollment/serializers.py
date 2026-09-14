from rest_framework import serializers

from neoskill.enrollment.models import Enrollment, EnrollmentRequest


class EnrollmentSerializer(serializers.ModelSerializer[Enrollment]):
    course_slug = serializers.CharField(source="course.slug", read_only=True)

    class Meta:
        model = Enrollment
        fields = ("id", "course", "course_slug", "status", "activated_at", "updated_at")
        read_only_fields = fields


class EnrollmentRequestCreateSerializer(serializers.Serializer[dict[str, str]]):
    note = serializers.CharField(
        max_length=1000, trim_whitespace=True, required=False, allow_blank=True, default=""
    )


class EnrollmentRequestSerializer(serializers.ModelSerializer[EnrollmentRequest]):
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = EnrollmentRequest
        fields = (
            "id",
            "course",
            "course_slug",
            "course_title",
            "user",
            "user_email",
            "user_name",
            "status",
            "note",
            "list_price",
            "referral_discount_percent",
            "requested_price",
            "requested_at",
            "reviewed_by",
            "reviewed_at",
        )
        read_only_fields = fields


class EnrollmentRequestQueueFilterSerializer(serializers.Serializer[dict[str, str]]):
    status = serializers.ChoiceField(
        choices=EnrollmentRequest.Status.choices,
        required=False,
        default=EnrollmentRequest.Status.PENDING,
    )
