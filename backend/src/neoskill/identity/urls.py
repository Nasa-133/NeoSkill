from django.urls import path
from rest_framework.routers import SimpleRouter

from neoskill.identity.admin_views import (
    AdminUserCourseAccessView,
    AdminUserPasswordView,
    AdminUserViewSet,
)
from neoskill.identity.views import (
    CsrfTokenView,
    DeviceListView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    SessionView,
)

router = SimpleRouter(trailing_slash=False)
router.register("admin/users", AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("auth/csrf", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/session", SessionView.as_view(), name="auth-session"),
    path("auth/devices", DeviceListView.as_view(), name="auth-devices"),
    path("auth/password-reset", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "auth/password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("admin/users/<uuid:pk>/password", AdminUserPasswordView.as_view()),
    path("admin/users/<uuid:pk>/courses", AdminUserCourseAccessView.as_view()),
    *router.urls,
]
