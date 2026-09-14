import uuid

from django.core.validators import URLValidator
from django.db import models


def validate_image_reference(value: str) -> None:
    """
    Accepts an absolute http(s) URL or a site-relative path.

    Uploads are stored under /api/v1/media/..., and keeping that reference relative
    means the same database works behind localhost, a LAN address or a real domain.
    """
    if not value or value.startswith("/"):
        return
    URLValidator(schemes=("http", "https"))(value)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Instructor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    title = models.CharField(max_length=180)
    photo_url = models.CharField(max_length=500, blank=True, validators=[validate_image_reference])
    experience = models.TextField(blank=True)
    bio = models.TextField(blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    social_links = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="courses")
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="courses")
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    short_description = models.CharField(max_length=320)
    description = models.TextField()
    image_url = models.CharField(max_length=500, blank=True, validators=[validate_image_reference])
    level = models.CharField(max_length=16, choices=Level.choices)
    language = models.CharField(max_length=40)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    sequential_learning = models.BooleanField(default=True)
    what_you_will_learn = models.JSONField(default=list, blank=True)
    audience = models.JSONField(default=list, blank=True)
    requirements = models.JSONField(default=list, blank=True)
    telegram_group_url = models.URLField(max_length=500, blank=True)
    support_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_free=True, price__isnull=True)
                    | models.Q(is_free=False, price__gt=0)
                ),
                name="catalog_course_coherent_price",
            )
        ]

    def __str__(self) -> str:
        return self.title


class Module(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=("course", "position"), name="catalog_module_position")
        ]

    def __str__(self) -> str:
        return self.title


class Topic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=("module", "position"), name="catalog_topic_position")
        ]

    def __str__(self) -> str:
        return self.title


class Lesson(models.Model):
    class Kind(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        TEXT = "TEXT", "Text"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    position = models.PositiveIntegerField()
    kind = models.CharField(max_length=8, choices=Kind.choices)
    content = models.TextField(blank=True)
    video_url = models.URLField(max_length=500, blank=True)
    material_url = models.URLField(max_length=500, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    free_preview = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=("topic", "position"), name="catalog_lesson_position")
        ]

    def __str__(self) -> str:
        return self.title


class Practice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="practice")
    instructions = models.TextField()
    example = models.TextField(blank=True)
    resource_url = models.URLField(max_length=500, blank=True)
    is_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Practice: {self.topic}"


class TopicTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name="test")
    passing_score = models.PositiveSmallIntegerField()
    question_count = models.PositiveSmallIntegerField(null=True, blank=True)
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(passing_score__gte=0, passing_score__lte=100),
                name="catalog_test_passing_score_range",
            ),
            models.CheckConstraint(
                condition=models.Q(question_count__isnull=True) | models.Q(question_count__gt=0),
                name="catalog_test_question_count_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Test: {self.topic}"


class CourseFAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=300)
    answer = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(fields=("course", "position"), name="catalog_faq_position")
        ]

    def __str__(self) -> str:
        return self.question


class Testimonial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_name = models.CharField(max_length=160)
    author_title = models.CharField(max_length=180, blank=True)
    quote = models.TextField()
    photo_url = models.CharField(max_length=500, blank=True, validators=[validate_image_reference])
    is_published = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")

    def __str__(self) -> str:
        return self.author_name
