from django.urls import path

from neoskill.platform.views import AdminSettingsView, PublicSettingsView, TestEmailView

urlpatterns = [
    path("settings/public", PublicSettingsView.as_view()),
    path("admin/settings", AdminSettingsView.as_view()),
    path("admin/settings/test-email", TestEmailView.as_view()),
]
