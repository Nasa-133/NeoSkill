import uuid

from django.conf import settings
from django.db import models

from neoskill.catalog.models import Course


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    activated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "course"), name="enrollment_one_per_course")
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.course}"


class EnrollmentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollment_requests",
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollment_requests")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_enrollment_requests",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    referral_discount_percent = models.PositiveSmallIntegerField(default=0)
    requested_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "course"),
                condition=models.Q(status="PENDING"),
                name="enrollment_one_pending_request",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="PENDING", reviewed_at__isnull=True, reviewed_by__isnull=True)
                    | models.Q(status__in=("APPROVED", "REJECTED"), reviewed_at__isnull=False)
                ),
                name="enrollment_request_review_state",
            ),
            models.CheckConstraint(
                condition=models.Q(referral_discount_percent__lte=100),
                name="enrollment_request_referral_discount_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.course} ({self.status})"
