from django.urls import include, path

from .views import register

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("register/", register, name="register"),
]
