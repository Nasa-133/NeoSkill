import uuid

from django.conf import settings
from django.db import models

from neoskill.catalog.models import TopicTest


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(TopicTest, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("test", "position"), name="assessment_question_position"
            )
        ]

    def __str__(self) -> str:
        return self.text


class QuestionOption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    position = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("question", "position"), name="assessment_option_position"
            ),
            models.UniqueConstraint(
                fields=("question",),
                condition=models.Q(is_correct=True),
                name="assessment_one_correct_option",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gte=1, position__lte=4),
                name="assessment_option_position_range",
            ),
        ]

    def __str__(self) -> str:
        return self.text


class TestAttempt(models.Model):
    class Result(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        PASSED = "PASSED", "Passed"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_attempts",
    )
    test = models.ForeignKey(TopicTest, on_delete=models.CASCADE, related_name="attempts")
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=Result.choices, default=Result.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-started_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__isnull=True) | models.Q(score__gte=0, score__lte=100),
                name="assessment_attempt_score_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(result="IN_PROGRESS", score__isnull=True, completed_at__isnull=True)
                    | models.Q(
                        result__in=("PASSED", "FAILED"),
                        score__isnull=False,
                        completed_at__isnull=False,
                    )
                ),
                name="assessment_attempt_result_state",
            ),
        ]


class TestAttemptAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempt_answers")
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.PROTECT,
        related_name="attempt_answers",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "question"), name="assessment_one_answer_per_question"
            )
        ]
