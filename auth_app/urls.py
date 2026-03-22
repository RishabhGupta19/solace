from django.urls import path
from .views import RegisterView, LoginView, RefreshView, MeView, SetRoleView,UpdateProfileView,SaveFCMTokenView

urlpatterns = [
    path("register", RegisterView.as_view()),
    path("login",    LoginView.as_view()),
    path("refresh",  RefreshView.as_view()),
    path("me",       MeView.as_view()),
    path("role",     SetRoleView.as_view()),
    path("profile",  UpdateProfileView.as_view()),
    path("fcm-token", SaveFCMTokenView.as_view()),
]
