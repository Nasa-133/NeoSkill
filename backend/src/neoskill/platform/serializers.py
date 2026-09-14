import re
from typing import Any

from django.conf import settings
from rest_framework import serializers

from neoskill.platform.models import PlatformSettings
from neoskill.platform.services import encrypt_password

PUBLIC_FIELDS = (
    "platform_name",
    "footer_text",
    "company_name",
    "about_title",
    "about_text",
    "company_address",
    "support_email",
    "support_telegram",
    "support_phone",
    "working_hours",
)


class PublicSettingsSerializer(serializers.ModelSerializer[PlatformSettings]):
    class Meta:
        model = PlatformSettings
        fields: tuple[str, ...] = PUBLIC_FIELDS


class AdminSettingsSerializer(PublicSettingsSerializer):
    smtp_password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, trim_whitespace=False, max_length=1024
    )
    smtp_password_set = serializers.SerializerMethodField()

    class Meta(PublicSettingsSerializer.Meta):
        fields = (
            *PUBLIC_FIELDS,
            "smtp_source",
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_security",
            "smtp_from_email",
            "smtp_password",
            "smtp_password_set",
            "updated_at",
        )
        read_only_fields = ("updated_at",)
        extra_kwargs = {"about_text": {"max_length": 20000}}

    def get_smtp_password_set(self, obj: PlatformSettings) -> bool:
        if obj.smtp_source == "ENV":
            return bool(getattr(settings, "EMAIL_HOST_PASSWORD", ""))
        return bool(obj.smtp_password_encrypted)

    def to_representation(self, instance: PlatformSettings) -> dict[str, Any]:
        result = super().to_representation(instance)
        if instance.smtp_source == "ENV":
            result.update(
                smtp_host=getattr(settings, "EMAIL_HOST", ""),
                smtp_port=getattr(settings, "EMAIL_PORT", 587),
                smtp_username=getattr(settings, "EMAIL_HOST_USER", ""),
                smtp_from_email=settings.DEFAULT_FROM_EMAIL,
                smtp_security="SSL"
                if getattr(settings, "EMAIL_USE_SSL", False)
                else "TLS"
                if getattr(settings, "EMAIL_USE_TLS", False)
                else "NONE",
            )
        return result

    def validate_support_telegram(self, value: str) -> str:
        value = value.strip().removeprefix("https://t.me/").removeprefix("@").rstrip("/")
        if value and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", value):
            raise serializers.ValidationError(
                "Telegram username yoki https://t.me/username kiriting."
            )
        return value

    def validate_support_phone(self, value: str) -> str:
        if value and not re.fullmatch(r"\+?[0-9 ()-]{7,30}", value):
            raise serializers.ValidationError("Telefon raqamini xalqaro formatda kiriting.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for name in ("platform_name", "smtp_username"):
            if any(ord(char) < 32 for char in attrs.get(name, "")):
                raise serializers.ValidationError({name: "Yaroqsiz boshqaruv belgisi."})
        obj = self.instance or PlatformSettings()
        source = attrs.get("smtp_source", obj.smtp_source)
        if source == "ADMIN":
            for name in ("smtp_host", "smtp_username", "smtp_from_email"):
                if not attrs.get(name, getattr(obj, name)):
                    raise serializers.ValidationError(
                        {name: "Email xizmati uchun bu maydon majburiy."}
                    )
            host = attrs.get("smtp_host", obj.smtp_host)
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", host):
                raise serializers.ValidationError(
                    {"smtp_host": "SMTP server nomini kiriting, URL emas."}
                )
            port = attrs.get("smtp_port", obj.smtp_port)
            if not 1 <= port <= 65535:
                raise serializers.ValidationError({"smtp_port": "Port 1–65535 oralig‘ida bo‘lsin."})
            if not attrs.get("smtp_password") and not obj.smtp_password_encrypted:
                inherited = (
                    getattr(settings, "EMAIL_HOST_PASSWORD", "") if obj.smtp_source == "ENV" else ""
                )
                if not inherited:
                    raise serializers.ValidationError({"smtp_password": "SMTP parolini kiriting."})
                attrs["smtp_password"] = inherited
        return attrs

    def update(
        self, instance: PlatformSettings, validated_data: dict[str, Any]
    ) -> PlatformSettings:
        password = validated_data.pop("smtp_password", "")
        if password:
            instance.smtp_password_encrypted = encrypt_password(password)
        return super().update(instance, validated_data)


class TestEmailSerializer(serializers.Serializer[dict[str, str]]):
    email = serializers.EmailField()
