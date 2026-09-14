import secrets
import uuid
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator
from django.db import models

REFERRAL_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_referral_code() -> str:
    """Return a compact, copy-friendly 72-bit referral identifier."""

    return "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(12))


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(
        self, email: str | None = None, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("role", User.Role.STUDENT)
        extra_fields.setdefault("is_staff", False)
        normalized_email = self.normalize_email(email) if email else None
        user = self.model(email=normalized_email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        if not email:
            raise ValueError("Superuser email is required.")
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if (
            extra_fields.get("role") != User.Role.ADMIN
            or extra_fields.get("is_staff") is not True
            or extra_fields.get("is_superuser") is not True
        ):
            raise ValueError("Superuser must have the ADMIN role and staff/superuser flags.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=64, blank=True, default="")
    last_name = models.CharField(max_length=64, blank=True, default="")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    referral_code = models.CharField(
        max_length=12, unique=True, editable=False, default=generate_referral_code
    )
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referred_users",
    )
    referral_discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)]
    )
    referral_discount_applied = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(100)]
    )

    objects = UserManager()

    USERNAME_FIELD: ClassVar[str] = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        ordering = ("date_joined",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(role="ADMIN", is_staff=True) | models.Q(role="STUDENT", is_staff=False)
                ),
                name="identity_role_matches_staff",
            ),
            models.CheckConstraint(
                condition=models.Q(referral_discount_percent__lte=100),
                name="identity_referral_discount_percent_range",
            ),
            models.CheckConstraint(
                condition=models.Q(referral_discount_applied__lte=100),
                name="identity_referral_discount_applied_range",
            ),
            models.CheckConstraint(
                condition=~models.Q(id=models.F("referred_by")),
                name="identity_referral_no_self_reference",
            ),
        ]

    def __str__(self) -> str:
        return self.email or str(self.pk)

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()


class LoginThrottle(models.Model):
    """Brute-force guard kept in PostgreSQL, because the MVP runs without Redis."""

    key_digest = models.CharField(max_length=64, unique=True)
    window_started_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("window_started_at",)


class DeviceSession(models.Model):
    """
    One row per browser signed into an account.

    An account may hold at most settings.AUTH_DEVICE_SESSION_LIMIT of these. A further
    sign-in is refused until the person picks one of the existing devices to release,
    which deletes both this row and the Django session behind it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_sessions")
    session_key = models.CharField(max_length=40, unique=True)
    device_id = models.UUIDField()
    device_name = models.CharField(max_length=64)
    user_agent = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "device_id"), name="identity_one_session_per_device"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} · {self.device_name}"
