from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from neoskill.identity.models import User


class Command(BaseCommand):
    help = "Promote an existing account to NeoSkill admin."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--email", type=str, required=True)

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"].strip().lower()
        user = User.objects.select_for_update().filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f"No account found for {email}.")
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=("role", "is_staff", "is_superuser", "updated_at"))
        self.stdout.write(self.style.SUCCESS(f"Admin access granted to {email}."))
