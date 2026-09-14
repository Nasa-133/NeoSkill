from rest_framework import serializers

from neoskill.assessment.models import TestAttempt
from neoskill.identity.models import User


class AdminUserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "role", "is_active", "date_joined")


class AdminTestAttemptSerializer(serializers.ModelSerializer[TestAttempt]):
    topic_id = serializers.UUIDField(source="test.topic_id", read_only=True)
    topic_title = serializers.CharField(source="test.topic.title", read_only=True)
    course_slug = serializers.CharField(source="test.topic.module.course.slug", read_only=True)

    class Meta:
        model = TestAttempt
        fields = (
            "id",
            "course_slug",
            "topic_id",
            "topic_title",
            "score",
            "result",
            "started_at",
            "completed_at",
        )
