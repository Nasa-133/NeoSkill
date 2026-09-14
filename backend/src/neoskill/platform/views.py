from smtplib import SMTPException

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.db import transaction
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.identity.access import IsAdmin
from neoskill.platform.models import PlatformSettings
from neoskill.platform.serializers import (
    AdminSettingsSerializer,
    PublicSettingsSerializer,
    TestEmailSerializer,
)
from neoskill.platform.services import current_settings, send_platform_email


class PublicSettingsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request) -> Response:
        return Response(
            PublicSettingsSerializer(current_settings()).data, headers={"Cache-Control": "no-store"}
        )


class AdminSettingsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request: Request) -> Response:
        return Response(
            AdminSettingsSerializer(current_settings()).data, headers={"Cache-Control": "no-store"}
        )

    @transaction.atomic
    def patch(self, request: Request) -> Response:
        PlatformSettings.objects.get_or_create(pk=1)
        config = PlatformSettings.objects.select_for_update().get(pk=1)
        serializer = AdminSettingsSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data, headers={"Cache-Control": "no-store"})


class TestEmailView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request: Request) -> Response:
        serializer = TestEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if current_settings().smtp_source == "ENV" and settings.EMAIL_BACKEND.endswith(
            ".console.EmailBackend"
        ):
            return Response(
                {"detail": "Xat yuborish uchun avval SMTP sozlamalarini kiriting."}, status=400
            )
        try:
            sent = send_platform_email(
                subject="NeoSkill — email sozlamalari testi",
                message="Test xati yetib keldi. Email xizmati ishlayapti.",
                recipient=serializer.validated_data["email"],
            )
        except (SMTPException, OSError, InvalidToken, ValueError):
            return Response(
                {"detail": "Xat yuborilmadi. SMTP server, port va parolni tekshiring."},
                status=502,
            )
        if not sent:
            return Response({"detail": "Email xizmati xatni qabul qilmadi."}, status=502)
        return Response(
            {"detail": "Test xati yuborildi. Kiruvchi xatlar va Spam papkasini tekshiring."}
        )
