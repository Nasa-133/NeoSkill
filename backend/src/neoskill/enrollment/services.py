from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from neoskill.catalog.models import Course
from neoskill.enrollment.models import Enrollment, EnrollmentRequest
from neoskill.identity.models import User


class CourseIsNotFree(ValueError):
    pass


class CourseIsFree(ValueError):
    pass


class AlreadyEnrolled(ValueError):
    pass


class EnrollmentRequestConflict(ValueError):
    pass


@dataclass(frozen=True)
class EnrollmentResult:
    enrollment: Enrollment
    created: bool


@dataclass(frozen=True)
class EnrollmentRequestResult:
    request: EnrollmentRequest
    created: bool


@dataclass(frozen=True)
class EnrollmentReviewResult:
    request: EnrollmentRequest
    enrollment: Enrollment | None


@transaction.atomic
def enroll_in_free_course(*, user: User, course: Course) -> EnrollmentResult:
    if not course.is_free:
        raise CourseIsNotFree
    enrollment, created = Enrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={"status": Enrollment.Status.ACTIVE},
    )
    return EnrollmentResult(enrollment=enrollment, created=created)


@transaction.atomic
def request_paid_enrollment(
    *, user: User, course: Course, note: str = ""
) -> EnrollmentRequestResult:
    if course.is_free:
        raise CourseIsFree
    if Enrollment.objects.filter(
        user=user, course=course, status=Enrollment.Status.ACTIVE
    ).exists():
        raise AlreadyEnrolled
    request, created = EnrollmentRequest.objects.get_or_create(
        user=user,
        course=course,
        status=EnrollmentRequest.Status.PENDING,
        defaults={
            "note": note,
            "list_price": course.price,
            "referral_discount_percent": user.referral_discount_applied,
            "requested_price": (
                course.price
                * (Decimal(100) - Decimal(user.referral_discount_applied))
                / Decimal(100)
            ).quantize(Decimal("0.01"))
            if course.price is not None
            else None,
        },
    )
    return EnrollmentRequestResult(request=request, created=created)


@transaction.atomic
def review_enrollment_request(
    *, request_id: UUID, reviewer: User, decision: str
) -> EnrollmentReviewResult:
    enrollment_request = EnrollmentRequest.objects.select_for_update().get(pk=request_id)
    target_status = {
        "approve": EnrollmentRequest.Status.APPROVED,
        "reject": EnrollmentRequest.Status.REJECTED,
    }.get(decision)
    if target_status is None:
        raise ValueError("Invalid enrollment decision.")
    if enrollment_request.status not in (EnrollmentRequest.Status.PENDING, target_status):
        raise EnrollmentRequestConflict

    enrollment: Enrollment | None = None
    if target_status == EnrollmentRequest.Status.APPROVED:
        enrollment, _ = Enrollment.objects.get_or_create(
            user=enrollment_request.user,
            course=enrollment_request.course,
            defaults={"status": Enrollment.Status.ACTIVE},
        )
    if enrollment_request.status == EnrollmentRequest.Status.PENDING:
        enrollment_request.status = target_status
        enrollment_request.reviewed_by = reviewer
        enrollment_request.reviewed_at = timezone.now()
        enrollment_request.save(update_fields=("status", "reviewed_by", "reviewed_at"))
    return EnrollmentReviewResult(request=enrollment_request, enrollment=enrollment)
