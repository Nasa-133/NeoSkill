from django.urls import path

from neoskill.learning.admin_views import (
    AdminAttemptStatsView,
    AdminEnrollmentStatsView,
    AdminStatsView,
    AdminUserProgressView,
)
from neoskill.learning.views import (
    ContinueLearningView,
    CourseLearningNavigationView,
    LessonCompletionView,
    MyCourseListView,
    StudentLessonDetailView,
    TopicPracticeView,
)

urlpatterns = [
    path("admin/stats", AdminStatsView.as_view()),
    path("admin/statistics/enrollments", AdminEnrollmentStatsView.as_view()),
    path("admin/statistics/attempts", AdminAttemptStatsView.as_view()),
    path("admin/users/<uuid:pk>/progress", AdminUserProgressView.as_view()),
    path("me/courses", MyCourseListView.as_view()),
    path("learning/courses/<slug:slug>", CourseLearningNavigationView.as_view()),
    path("learning/courses/<slug:slug>/continue", ContinueLearningView.as_view()),
    path("learning/lessons/<uuid:pk>", StudentLessonDetailView.as_view()),
    path("learning/lessons/<uuid:pk>/complete", LessonCompletionView.as_view()),
    path("learning/topics/<uuid:pk>/practice", TopicPracticeView.as_view()),
]
