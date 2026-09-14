"""Password authentication, a PostgreSQL attempt throttle and the device limit."""

import hashlib
from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.sessions.models import Session
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from neoskill.identity.models import DeviceSession, LoginThrottle, User

LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW_SECONDS = 600


@dataclass(frozen=True)
class LoginResult:
    user: User | None
    throttled: bool = False
    device_limit: bool = False
    devices: tuple[DeviceSession, ...] = field(default_factory=tuple)


def throttle_key(email: str, ip: str | None) -> str:
    return hashlib.sha256(f"{email}|{ip or ''}|{settings.SECRET_KEY}".encode()).hexdigest()


@transaction.atomic
def _consume_attempt(key: str) -> bool:
    """Returns True when the caller has already exhausted the window."""
    now = timezone.now()
    window = timedelta(seconds=LOGIN_ATTEMPT_WINDOW_SECONDS)
    record, _ = LoginThrottle.objects.select_for_update().get_or_create(
        key_digest=key, defaults={"window_started_at": now, "attempts": 0}
    )
    if now - record.window_started_at > window:
        record.window_started_at = now
        record.attempts = 0
    if record.attempts >= LOGIN_ATTEMPT_LIMIT:
        record.save(update_fields=("window_started_at", "attempts", "updated_at"))
        return True
    record.attempts += 1
    record.save(update_fields=("window_started_at", "attempts", "updated_at"))
    return False


def clear_attempts(key: str) -> None:
    LoginThrottle.objects.filter(key_digest=key).delete()


def release_device(user: User, device_session_id: UUID) -> bool:
    """Signs one device out: drops the Django session, then the tracking row."""
    record = DeviceSession.objects.filter(user=user, pk=device_session_id).first()
    if record is None:
        return False
    Session.objects.filter(session_key=record.session_key).delete()
    record.delete()
    return True


def active_devices(user: User) -> tuple[DeviceSession, ...]:
    """Rows whose Django session still exists; stale ones are cleaned up on the way."""
    records = list(DeviceSession.objects.filter(user=user))
    live_keys = set(
        Session.objects.filter(session_key__in=[item.session_key for item in records]).values_list(
            "session_key", flat=True
        )
    )
    stale = [item.pk for item in records if item.session_key not in live_keys]
    if stale:
        DeviceSession.objects.filter(pk__in=stale).delete()
    return tuple(item for item in records if item.session_key in live_keys)


def forget_current_device(request: HttpRequest) -> None:
    if request.session.session_key:
        DeviceSession.objects.filter(session_key=request.session.session_key).delete()


def touch_current_device(request: HttpRequest) -> None:
    if request.session.session_key:
        DeviceSession.objects.filter(session_key=request.session.session_key).update(
            last_seen_at=timezone.now()
        )


@transaction.atomic
def start_session(
    request: HttpRequest,
    user: User,
    *,
    device_id: UUID,
    device_name: str,
    user_agent: str = "",
    revoke: UUID | None = None,
) -> LoginResult:
    """
    Opens a session for one device, enforcing the account's device limit.

    A device that is already registered simply reconnects. Otherwise the limit is
    checked first, and the caller must name a device to release before a new one fits.
    """
    # Serialize every login for this account. Locking only existing DeviceSession rows
    # is insufficient when two brand-new devices arrive together because neither query
    # has a row to lock and both could observe one free slot.
    User.objects.select_for_update().get(pk=user.pk)
    if revoke is not None:
        release_device(user, revoke)

    existing = DeviceSession.objects.select_for_update().filter(user=user, device_id=device_id)
    reconnecting = existing.first()
    if reconnecting is None and len(active_devices(user)) >= settings.AUTH_DEVICE_SESSION_LIMIT:
        return LoginResult(user=None, device_limit=True, devices=active_devices(user))

    if reconnecting is not None:
        Session.objects.filter(session_key=reconnecting.session_key).delete()
        reconnecting.delete()

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.save()
    DeviceSession.objects.create(
        user=user,
        session_key=request.session.session_key or "",
        device_id=device_id,
        device_name=device_name[:64] or "Brauzer",
        user_agent=user_agent[:200],
    )
    return LoginResult(user=user)


def authenticate_with_password(
    request: HttpRequest,
    *,
    email: str,
    password: str,
    ip: str | None,
    device_id: UUID,
    device_name: str,
    user_agent: str = "",
    revoke: UUID | None = None,
) -> LoginResult:
    key = throttle_key(email, ip)
    if _consume_attempt(key):
        return LoginResult(user=None, throttled=True)
    user = authenticate(request, username=email, password=password)
    if not isinstance(user, User) or not user.is_active:
        return LoginResult(user=None)
    result = start_session(
        request,
        user,
        device_id=device_id,
        device_name=device_name,
        user_agent=user_agent,
        revoke=revoke,
    )
    if result.user is not None:
        clear_attempts(key)
    return result
