from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from neoskill.identity.models import User

pytestmark = pytest.mark.django_db


def test_account_is_promoted_idempotently():
    User.objects.create_user(email="owner@example.com", password="Str0ng-Passw0rd")
    output = StringIO()
    call_command("grant_admin", email="owner@example.com", stdout=output)
    call_command("grant_admin", email="OWNER@example.com", stdout=output)

    user = User.objects.get(email="owner@example.com")
    assert user.role == User.Role.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


def test_unknown_email_is_rejected():
    with pytest.raises(CommandError):
        call_command("grant_admin", email="nobody@example.com")
