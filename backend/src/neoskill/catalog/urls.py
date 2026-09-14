from django.urls import path
from rest_framework.routers import SimpleRouter

from neoskill.catalog.uploads import AdminImageUploadView, MediaFileView
from neoskill.catalog.views import (
    AdminCategoryViewSet,
    AdminCourseCurriculumView,
    AdminCourseFAQViewSet,
    AdminCourseViewSet,
    AdminInstructorViewSet,
    AdminLessonViewSet,
    AdminModuleViewSet,
    AdminPracticeViewSet,
    AdminReorderView,
    AdminTestimonialViewSet,
    AdminTopicTestViewSet,
    AdminTopicViewSet,
    PublicCategoryListView,
    PublicCourseDetailView,
    PublicCourseListView,
    PublicInstructorListView,
    PublicLessonPreviewView,
    PublicTestimonialListView,
)

router = SimpleRouter(trailing_slash=False)
router.register("admin/categories", AdminCategoryViewSet, basename="admin-category")
router.register("admin/instructors", AdminInstructorViewSet, basename="admin-instructor")
router.register("admin/courses", AdminCourseViewSet, basename="admin-course")
router.register("admin/modules", AdminModuleViewSet, basename="admin-module")
router.register("admin/topics", AdminTopicViewSet, basename="admin-topic")
router.register("admin/lessons", AdminLessonViewSet, basename="admin-lesson")
router.register("admin/practices", AdminPracticeViewSet, basename="admin-practice")
router.register("admin/topic-tests", AdminTopicTestViewSet, basename="admin-topic-test")
router.register("admin/course-faqs", AdminCourseFAQViewSet, basename="admin-course-faq")
router.register("admin/testimonials", AdminTestimonialViewSet, basename="admin-testimonial")

urlpatterns = [
    path("admin/uploads/image", AdminImageUploadView.as_view()),
    path("media/<path:path>", MediaFileView.as_view()),
    path("courses", PublicCourseListView.as_view()),
    path("categories", PublicCategoryListView.as_view()),
    path("instructors", PublicInstructorListView.as_view()),
    path("testimonials", PublicTestimonialListView.as_view()),
    path("courses/<slug:slug>", PublicCourseDetailView.as_view()),
    path("lessons/<uuid:pk>/preview", PublicLessonPreviewView.as_view()),
    path(
        "admin/courses/<uuid:course_id>/curriculum",
        AdminCourseCurriculumView.as_view(),
    ),
    path(
        "admin/courses/<uuid:parent_id>/modules/reorder",
        AdminReorderView.as_view(target="modules"),
    ),
    path(
        "admin/modules/<uuid:parent_id>/topics/reorder",
        AdminReorderView.as_view(target="topics"),
    ),
    path(
        "admin/topics/<uuid:parent_id>/lessons/reorder",
        AdminReorderView.as_view(target="lessons"),
    ),
    *router.urls,
]
