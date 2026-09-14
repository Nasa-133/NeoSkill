from django.conf import settings
from django.db import models


class PlatformSettings(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    platform_name = models.CharField(max_length=100, default="NeoSkill")
    footer_text = models.CharField(
        max_length=300, default="O‘rganing. Amalda bajaring. Natijaga erishing."
    )
    company_name = models.CharField(max_length=200, default="NeoSkill")
    about_title = models.CharField(
        max_length=200, default="Ta’limni aniq yo‘l va amaliy natijaga aylantiramiz"
    )
    about_text = models.TextField(
        default="NeoSkill — zamonaviy kasblarni izchil o‘rganish platformasi."
    )
    company_address = models.CharField(max_length=500, blank=True)
    support_email = models.EmailField(blank=True)
    support_telegram = models.CharField(max_length=100, blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    working_hours = models.CharField(max_length=200, blank=True)
    smtp_source = models.CharField(
        max_length=12, choices=[("ENV", "Environment"), ("ADMIN", "Admin")], default="ENV"
    )
    smtp_host = models.CharField(max_length=253, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=254, blank=True)
    smtp_password_encrypted = models.TextField(blank=True)
    smtp_security = models.CharField(
        max_length=12,
        choices=[("TLS", "STARTTLS"), ("SSL", "SSL/TLS"), ("NONE", "None")],
        default="TLS",
    )
    smtp_from_email = models.EmailField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="platform_settings_singleton")
        ]
