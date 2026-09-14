from django.urls import include, path

from neoskill.config import http_errors

urlpatterns = [
    path("api/v1/", include("neoskill.platform.urls")),
    path("api/v1/", include("neoskill.health.urls")),
    path("api/v1/", include("neoskill.identity.urls")),
    path("api/v1/", include("neoskill.referral.urls")),
    path("api/v1/", include("neoskill.catalog.urls")),
    path("api/v1/", include("neoskill.assessment.urls")),
    path("api/v1/", include("neoskill.enrollment.urls")),
    path("api/v1/", include("neoskill.learning.urls")),
]

handler400 = http_errors.bad_request
handler403 = http_errors.permission_denied
handler404 = http_errors.not_found
handler500 = http_errors.server_error
