from neoskill.catalog.models import Course
from neoskill.enrollment.models import Enrollment
from neoskill.identity.models import User


def has_active_enrollment(*, user: User, course: Course) -> bool:
    return Enrollment.objects.filter(
        user=user,
        course=course,
        status=Enrollment.Status.ACTIVE,
    ).exists()
