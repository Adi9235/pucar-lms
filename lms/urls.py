from django.contrib import admin
from django.urls import include, path

from accounts.views import home

urlpatterns = [
    path("", home, name="home"),
    path("", include("accounts.urls")),
    path("", include("courses.urls")),
    path("", include("quizzes.urls")),
    path("admin/", admin.site.urls),
]
