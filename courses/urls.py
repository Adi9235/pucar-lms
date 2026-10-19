from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    # Learner
    path("courses/", views.CatalogueView.as_view(), name="catalogue"),
    path("courses/mine/", views.MyCoursesView.as_view(), name="my_courses"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="detail"),
    path("courses/<int:pk>/enrol/", views.EnrolView.as_view(), name="enrol"),
    path(
        "courses/<int:pk>/lessons/<int:lesson_pk>/",
        views.LessonDetailView.as_view(),
        name="lesson",
    ),
    path(
        "courses/<int:pk>/lessons/<int:lesson_pk>/complete/",
        views.CompleteLessonView.as_view(),
        name="lesson_complete",
    ),
    # Instructor
    path("teach/", views.TeachCourseListView.as_view(), name="teach_list"),
    path("teach/new/", views.CourseCreateView.as_view(), name="course_create"),
    path("teach/<int:pk>/", views.CourseManageView.as_view(), name="course_manage"),
    path("teach/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="course_update"),
    path("teach/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),
    path("teach/<int:pk>/dashboard/", views.CourseDashboardView.as_view(), name="dashboard"),
    path("teach/<int:pk>/lessons/new/", views.LessonCreateView.as_view(), name="lesson_create"),
    path(
        "teach/<int:pk>/lessons/<int:lesson_pk>/edit/",
        views.LessonUpdateView.as_view(),
        name="lesson_update",
    ),
    path(
        "teach/<int:pk>/lessons/<int:lesson_pk>/delete/",
        views.LessonDeleteView.as_view(),
        name="lesson_delete",
    ),
]
