from django.urls import path

from neoskill.enrollment.views import (
    AdminEnrollmentRequestDecisionView,
    AdminEnrollmentRequestDetailView,
    AdminEnrollmentRequestListView,
    FreeCourseEnrollmentView,
    PaidEnrollmentRequestView,
)

urlpatterns = [
    path("courses/<slug:slug>/enroll/free", FreeCourseEnrollmentView.as_view()),
    path("courses/<slug:slug>/enrollment-requests", PaidEnrollmentRequestView.as_view()),
    path("admin/enrollment-requests", AdminEnrollmentRequestListView.as_view()),
    path(
        "admin/enrollment-requests/<uuid:pk>/approve",
        AdminEnrollmentRequestDecisionView.as_view(decision="approve"),
    ),
    path(
        "admin/enrollment-requests/<uuid:pk>/reject",
        AdminEnrollmentRequestDecisionView.as_view(decision="reject"),
    ),
    path(
        "admin/enrollment-requests/<uuid:pk>",
        AdminEnrollmentRequestDetailView.as_view(),
    ),
]
