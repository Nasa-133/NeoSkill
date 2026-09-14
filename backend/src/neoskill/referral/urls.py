from django.urls import path

from neoskill.referral.views import (
    AdminReferralDetailView,
    AdminReferralListView,
    MyReferralView,
    ReferralOfferView,
)

urlpatterns = [
    path("referrals/<str:code>", ReferralOfferView.as_view()),
    path("me/referral", MyReferralView.as_view()),
    path("admin/referrals", AdminReferralListView.as_view()),
    path("admin/referrals/<uuid:pk>", AdminReferralDetailView.as_view()),
]
