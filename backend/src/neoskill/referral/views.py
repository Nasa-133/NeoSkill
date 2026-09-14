from uuid import UUID

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.enrollment.models import Enrollment
from neoskill.identity.access import IsAdmin, IsAuthenticatedUser
from neoskill.identity.models import User
from neoskill.referral.serializers import ReferralCodeSerializer, ReferralDiscountSerializer


def referral_counts(user: User) -> dict[str, int]:
    referred = User.objects.filter(referred_by=user)
    return {
        "referred_count": referred.count(),
        "referred_with_access": referred.filter(enrollments__status=Enrollment.Status.ACTIVE)
        .distinct()
        .count(),
        "free_access_count": Enrollment.objects.filter(
            user__referred_by=user,
            status=Enrollment.Status.ACTIVE,
            course__is_free=True,
        ).count(),
        "paid_access_count": Enrollment.objects.filter(
            user__referred_by=user,
            status=Enrollment.Status.ACTIVE,
            course__is_free=False,
        ).count(),
    }


def invited_by_name(user: User) -> str:
    inviter = user.referred_by
    return inviter.full_name if inviter is not None else ""


def inviter_payload(user: User) -> dict[str, object]:
    return {
        "user_id": str(user.pk),
        "email": user.email,
        "full_name": user.full_name,
        "referral_code": user.referral_code,
        "referral_path": f"/?ref={user.referral_code}",
        "discount_percent": user.referral_discount_percent,
        "applied_discount_percent": user.referral_discount_applied,
        "invited_by_name": invited_by_name(user),
        **referral_counts(user),
    }


class ReferralOfferView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request, code: str) -> Response:
        serializer = ReferralCodeSerializer(data={"code": code.upper()})
        serializer.is_valid(raise_exception=True)
        inviter = User.objects.filter(
            referral_code=serializer.validated_data["code"], is_active=True
        ).first()
        if inviter is None:
            return Response({"detail": "Taklif kodi topilmadi."}, status=404)
        return Response(
            {
                "code": inviter.referral_code,
                "inviter_name": inviter.full_name,
                "discount_percent": inviter.referral_discount_percent,
            }
        )


class MyReferralView(APIView):
    permission_classes = [IsAuthenticatedUser]
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            return Response({"detail": "Authentication required."}, status=403)
        return Response(inviter_payload(request.user))


class AdminReferralListView(APIView):
    permission_classes = [IsAdmin]
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "").strip()
        if len(search) > 100:
            return Response({"search": ["Qidiruv 100 belgidan oshmasin."]}, status=400)
        users = User.objects.annotate(
            referred_total=Count("referred_users", distinct=True),
            referred_access=Count(
                "referred_users",
                filter=Q(referred_users__enrollments__status=Enrollment.Status.ACTIVE),
                distinct=True,
            ),
            free_access=Count(
                "referred_users__enrollments",
                filter=Q(
                    referred_users__enrollments__status=Enrollment.Status.ACTIVE,
                    referred_users__enrollments__course__is_free=True,
                ),
                distinct=True,
            ),
            paid_access=Count(
                "referred_users__enrollments",
                filter=Q(
                    referred_users__enrollments__status=Enrollment.Status.ACTIVE,
                    referred_users__enrollments__course__is_free=False,
                ),
                distinct=True,
            ),
        )
        if search:
            users = users.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(referral_code__icontains=search)
            )
        users = users.select_related("referred_by").order_by(
            "-referred_total", "-referral_discount_percent", "-date_joined"
        )
        return Response(
            [
                {
                    "user_id": str(user.pk),
                    "email": user.email,
                    "full_name": user.full_name,
                    "referral_code": user.referral_code,
                    "referral_path": f"/?ref={user.referral_code}",
                    "discount_percent": user.referral_discount_percent,
                    "applied_discount_percent": user.referral_discount_applied,
                    "invited_by_name": invited_by_name(user),
                    "referred_count": user.referred_total,
                    "referred_with_access": user.referred_access,
                    "free_access_count": user.free_access,
                    "paid_access_count": user.paid_access,
                }
                for user in users
            ]
        )


class AdminReferralDetailView(APIView):
    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]

    def get(self, request: Request, pk: UUID) -> Response:
        inviter = get_object_or_404(User, pk=pk)
        referred = User.objects.filter(referred_by=inviter).prefetch_related("enrollments__course")
        return Response(
            {
                **inviter_payload(inviter),
                "referred_users": [
                    {
                        "id": str(user.pk),
                        "email": user.email,
                        "full_name": user.full_name,
                        "discount_percent": user.referral_discount_applied,
                        "joined_at": user.date_joined,
                        "course_access": [
                            {
                                "id": str(enrollment.pk),
                                "course_title": enrollment.course.title,
                                "access_type": "FREE" if enrollment.course.is_free else "PAID",
                                "activated_at": enrollment.activated_at,
                            }
                            for enrollment in user.enrollments.all()
                        ],
                    }
                    for user in referred
                ],
            }
        )

    def patch(self, request: Request, pk: UUID) -> Response:
        inviter = get_object_or_404(User, pk=pk)
        serializer = ReferralDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inviter.referral_discount_percent = serializer.validated_data["discount_percent"]
        inviter.save(update_fields=("referral_discount_percent", "updated_at"))
        return Response(inviter_payload(inviter))
