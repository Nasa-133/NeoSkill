from typing import Any

from django.db import migrations, models


def empty_phone_to_null(apps: Any, schema_editor: Any) -> None:
    TelegramIdentity = apps.get_model("identity", "TelegramIdentity")
    TelegramIdentity.objects.filter(phone_number="").update(phone_number=None)


class Migration(migrations.Migration):
    dependencies = [("identity", "0006_authdevicesession")]

    operations = [
        migrations.RunPython(empty_phone_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="telegramidentity",
            name="phone_number",
            field=models.CharField(blank=True, max_length=16, null=True, unique=True),
        ),
    ]
