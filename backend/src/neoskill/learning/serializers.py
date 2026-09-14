from rest_framework import serializers

from neoskill.catalog.models import Lesson, Practice
from neoskill.catalog.serializers import PublicCourseListSerializer
from neoskill.enrollment.models import Enrollment
from neoskill.learning.models import CourseProgress
from neoskill.learning.progress import calculate_course_progress


class StudentLessonSerializer(serializers.ModelSerializer[Lesson]):
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    course_slug = serializers.CharField(source="topic.module.course.slug", read_only=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "topic",
            "topic_title",
            "course_slug",
            "title",
            "position",
            "kind",
            "content",
            "video_url",
            "material_url",
            "duration_minutes",
            "is_required",
            "free_preview",
        )


class MyCourseSerializer(serializers.ModelSerializer[Enrollment]):
    course = PublicCourseListSerializer(read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ("id", "status", "activated_at", "course", "progress")

    def get_progress(self, obj: Enrollment) -> dict[str, object]:
        current_lesson_id = None
        try:
            current_lesson_id = obj.course_progress.current_lesson_id
        except CourseProgress.DoesNotExist:
            pass
        progress = calculate_course_progress(course=obj.course, user=obj.user)
        return {
            "required_units": progress.required_units,
            "completed_units": progress.completed_units,
            "percent": progress.percent,
            "is_complete": progress.is_complete,
            "current_lesson_id": current_lesson_id,
        }


class StudentPracticeSerializer(serializers.ModelSerializer[Practice]):
    topic_title = serializers.CharField(source="topic.title", read_only=True)
    course_slug = serializers.CharField(source="topic.module.course.slug", read_only=True)

    class Meta:
        model = Practice
        fields = (
            "id",
            "topic",
            "topic_title",
            "course_slug",
            "instructions",
            "example",
            "resource_url",
            "is_required",
        )
