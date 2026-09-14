import logging
from collections.abc import Iterable
from smtplib import SMTPException
from uuid import UUID

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.identity.access import IsAuthenticatedUser
from neoskill.identity.models import DeviceSession, User
from neoskill.identity.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    validate_account_password,
)
from neoskill.identity.session_auth import (
    active_devices,
    authenticate_with_password,
    forget_current_device,
    release_device,
    start_session,
    touch_current_device,
)
from neoskill.platform.services import current_settings, send_platform_email


def device_payload(devices: Iterable[DeviceSession]) -> list[dict[str, object]]:
    return [
        {
            "id": str(item.pk),
            "name": item.device_name,
            "created_at": item.created_at,
            "last_seen_at": item.last_seen_at,
        }
        for item in devices
    ]


def user_payload(user: User) -> dict[str, object]:
    return {
        "id": str(user.pk),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        return Response({"csrf": "ready"}, headers={"Cache-Control": "no-store"})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post", "options"]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inviter = None
        if referral_code := data.get("referral_code"):
            inviter = (
                User.objects.select_for_update()
                .filter(referral_code=referral_code, is_active=True)
                .first()
            )
            if inviter is None:
                return Response({"referral_code": ["Taklif kodi topilmadi."]}, status=400)
        user = User.objects.create_user(
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            referred_by=inviter,
            referral_discount_applied=(inviter.referral_discount_percent if inviter else 0),
        )
        start_session(
            request._request,
            user,
            device_id=data["device_id"],
            device_name=data.get("device_name", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return Response(
            {"user": user_payload(user), "first_login": True},
            status=201,
            headers={"Cache-Control": "no-store"},
        )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Email yoki parol noto‘g‘ri."}, status=400)
        data = serializer.validated_data
        result = authenticate_with_password(
            request._request,
            email=data["email"],
            password=data["password"],
            ip=request.META.get("REMOTE_ADDR"),
            device_id=data["device_id"],
            device_name=data.get("device_name", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            revoke=data.get("revoke_device_session_id"),
        )
        if result.throttled:
            return Response(
                {"detail": "Juda ko‘p urinish. Biroz kutib, qayta urinib ko‘ring."},
                status=429,
                headers={"Retry-After": "600"},
            )
        if result.device_limit:
            limit = settings.AUTH_DEVICE_SESSION_LIMIT
            return Response(
                {
                    "detail": (
                        f"Hisobda {limit} ta faol qurilma bor. "
                        "Davom etish uchun birini chiqarib yuboring."
                    ),
                    "code": "device_limit",
                    "devices": device_payload(result.devices),
                },
                status=409,
            )
        if result.user is None:
            # One message for both cases, so the endpoint cannot enumerate accounts.
            return Response({"detail": "Email yoki parol noto‘g‘ri."}, status=400)
        return Response(
            {"user": user_payload(result.user), "first_login": False},
            headers={"Cache-Control": "no-store"},
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None and user.email:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            platform_name = current_settings().platform_name
            try:
                send_platform_email(
                    subject=f"{platform_name} — parolni tiklash",
                    message=(
                        f"Salom{(' ' + user.first_name) if user.first_name else ''}!\n\n"
                        "Parolni tiklash uchun quyidagi havolani oching:\n"
                        f"{link}\n\n"
                        "Havola 2 soat amal qiladi va bir marta ishlatiladi.\n"
                        "Agar bu so‘rovni siz yubormagan bo‘lsangiz, xatni e’tiborsiz qoldiring."
                    ),
                    recipient=user.email,
                )
            except (SMTPException, OSError, InvalidToken, ValueError):
                # Keep the same response for known and unknown accounts; never log
                # SMTP credentials or a reset link in a transport failure.
                logging.getLogger(__name__).warning("Password reset email delivery failed.")
        # Always the same answer, so the endpoint cannot be used to probe emails.
        return Response({"detail": "Agar bunday hisob mavjud bo‘lsa, xat yuborildi."}, status=202)


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post", "options"]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user_id = UUID(force_str(urlsafe_base64_decode(data["uid"])))
            # Serialize token validation and password changes for the same account.
            user = User.objects.select_for_update().get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Havola yaroqsiz yoki muddati tugagan."}, status=400)
        if not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Havola yaroqsiz yoki muddati tugagan."}, status=400)
        validate_account_password(data["password"], user)
        user.set_password(data["password"])
        user.save(update_fields=("password", "updated_at"))
        return Response({"detail": "Parol yangilandi."}, status=200)


class SessionView(APIView):
    permission_classes = [IsAuthenticatedUser]
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            return Response({"detail": "Authentication required."}, status=403)
        touch_current_device(request._request)
        return Response({"user": user_payload(request.user)}, headers={"Cache-Control": "no-store"})


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedUser]
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        forget_current_device(request._request)
        logout(request._request)
        return Response(status=204)


class DeviceListView(APIView):
    """Lets a person see and release their own signed-in devices."""

    permission_classes = [IsAuthenticatedUser]
    http_method_names = ["get", "delete", "options"]

    def get(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            return Response({"detail": "Authentication required."}, status=403)
        current = request.session.session_key
        return Response(
            [
                {
                    "id": str(device.pk),
                    "name": device.device_name,
                    "created_at": device.created_at,
                    "last_seen_at": device.last_seen_at,
                    "current": device.session_key == current,
                }
                for device in active_devices(request.user)
            ]
        )

    def delete(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            return Response({"detail": "Authentication required."}, status=403)
        raw = request.query_params.get("id")
        if not raw:
            return Response({"detail": "id majburiy."}, status=400)
        try:
            device_id = UUID(raw)
        except ValueError:
            return Response({"detail": "id yaroqsiz."}, status=400)
        if not release_device(request.user, device_id):
            return Response({"detail": "Qurilma topilmadi."}, status=404)
        return Response(status=204)
