from django.urls import path
from rest_framework.routers import SimpleRouter

from neoskill.assessment.views import (
    AdminQuestionReorderView,
    AdminQuestionViewSet,
    StudentTopicTestAttemptListView,
    StudentTopicTestStatusView,
)

router = SimpleRouter(trailing_slash=False)
router.register("admin/questions", AdminQuestionViewSet, basename="admin-question")

urlpatterns = [
    path("learning/topics/<uuid:topic_id>/test", StudentTopicTestStatusView.as_view()),
    path(
        "learning/topics/<uuid:topic_id>/test/attempts",
        StudentTopicTestAttemptListView.as_view(),
    ),
    path(
        "admin/topic-tests/<uuid:test_id>/questions/reorder",
        AdminQuestionReorderView.as_view(),
    ),
    *router.urls,
]
