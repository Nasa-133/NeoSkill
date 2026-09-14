from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from neoskill.identity.models import User


def _clean_email(value: str) -> str:
    return value.strip().lower()


def validate_account_password(password: str, user: User) -> None:
    try:
        validate_password(password, user=user)
    except DjangoValidationError as error:
        raise serializers.ValidationError({"password": list(error.messages)}) from None


class PasswordField(serializers.CharField):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("write_only", True)
        kwargs.setdefault("min_length", 8)
        kwargs.setdefault("max_length", 128)
        kwargs.setdefault("trim_whitespace", False)
        super().__init__(**kwargs)

    def run_validation(self, data: Any = serializers.empty) -> Any:
        value = super().run_validation(data)
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from None
        return value


class DeviceFieldsMixin(serializers.Serializer[dict[str, object]]):
    """Every sign-in names the browser it comes from, so the device limit can be applied."""

    device_id = serializers.UUIDField()
    device_name = serializers.CharField(max_length=64, allow_blank=True, required=False, default="")

    def validate_device_name(self, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise serializers.ValidationError("Qurilma nomi yaroqsiz.")
        return value.strip() or "Brauzer"


class RegisterSerializer(DeviceFieldsMixin):
    email = serializers.EmailField(max_length=254)
    password = PasswordField()
    first_name = serializers.CharField(max_length=64, allow_blank=True, required=False, default="")
    last_name = serializers.CharField(max_length=64, allow_blank=True, required=False, default="")
    referral_code = serializers.RegexField(
        r"(?i)^[23456789A-HJ-NP-Z]{12}$", required=False, allow_blank=True, max_length=12
    )

    def validate_email(self, value: str) -> str:
        email = _clean_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Bu email bilan hisob allaqachon mavjud.")
        return email

    def validate_referral_code(self, value: str) -> str:
        return value.strip().upper()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = User(
            **{field: attrs.get(field, "") for field in ("email", "first_name", "last_name")}
        )
        validate_account_password(attrs["password"], user)
        return attrs


class LoginSerializer(DeviceFieldsMixin):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    revoke_device_session_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value: str) -> str:
        return _clean_email(value)


class PasswordResetRequestSerializer(serializers.Serializer[dict[str, object]]):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value: str) -> str:
        return _clean_email(value)


class PasswordResetConfirmSerializer(serializers.Serializer[dict[str, object]]):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)
    password = PasswordField()


class AdminUserSerializer(serializers.ModelSerializer[User]):
    """Admin-managed accounts; the password is set through its own endpoint."""

    password = PasswordField(required=False, allow_null=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "is_active",
            "date_joined",
            "referral_code",
            "referred_by",
            "referral_discount_percent",
            "referral_discount_applied",
            "password",
        )
        read_only_fields = (
            "id",
            "date_joined",
            "full_name",
            "referral_code",
            "referred_by",
            "referral_discount_applied",
        )

    def validate_email(self, value: str) -> str:
        email = _clean_email(value)
        existing = User.objects.filter(email__iexact=email)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("Bu email band.")
        return email

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Yangi hisob uchun parol majburiy."})
        if password := attrs.get("password"):
            # Validate against the resulting profile without mutating the saved account.
            user = User(
                **{
                    field: attrs.get(field, getattr(self.instance, field, ""))
                    for field in ("email", "first_name", "last_name")
                }
            )
            validate_account_password(password, user)
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password")
        role = validated_data.get("role", User.Role.STUDENT)
        validated_data["is_staff"] = role == User.Role.ADMIN
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        # The database constraint keeps role and staff flag in step.
        instance.is_staff = instance.role == User.Role.ADMIN
        if not instance.is_staff:
            instance.is_superuser = False
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SetPasswordSerializer(serializers.Serializer[dict[str, object]]):
    password = PasswordField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        validate_account_password(attrs["password"], self.context["user"])
        return attrs
