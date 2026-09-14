from django.urls import path

from neoskill.health.views import HealthView, ReadinessView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("readiness", ReadinessView.as_view(), name="readiness"),
]
