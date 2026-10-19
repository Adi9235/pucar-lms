from django.urls import path

from . import views

app_name = "quizzes"

urlpatterns = [
    # Instructor
    path("teach/<int:pk>/quiz/", views.QuizEditView.as_view(), name="quiz_edit"),
    path(
        "teach/<int:pk>/quiz/questions/new/",
        views.QuestionCreateView.as_view(),
        name="question_create",
    ),
    path(
        "teach/<int:pk>/quiz/questions/<int:question_pk>/edit/",
        views.QuestionUpdateView.as_view(),
        name="question_update",
    ),
    path(
        "teach/<int:pk>/quiz/questions/<int:question_pk>/delete/",
        views.QuestionDeleteView.as_view(),
        name="question_delete",
    ),
    # Learner
    path("courses/<int:pk>/quiz/", views.QuizTakeView.as_view(), name="take"),
    path("attempts/<int:pk>/", views.AttemptResultView.as_view(), name="attempt_result"),
]
