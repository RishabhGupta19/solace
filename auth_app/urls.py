from django.urls import path
from .views import RegisterView, LoginView, RefreshView, MeView, SetRoleView,SaveFCMTokenView,UpdateProfileView, UploadProfilePicView, ForgotPasswordView, VerifyOTPView, ResetPasswordView

urlpatterns = [
    path("register", RegisterView.as_view()),
    path("login",    LoginView.as_view()),
    path("refresh",  RefreshView.as_view()),
    path("me",       MeView.as_view()),
    path("role",     SetRoleView.as_view()),
    path("profile",  UpdateProfileView.as_view()),
    path("fcm-token", SaveFCMTokenView.as_view()),
    path("upload-profile-pic", UploadProfilePicView.as_view()),
     # NEW ROUTES for forgot password feature
    path("forgot-password", ForgotPasswordView.as_view()),
    path("verify-otp", VerifyOTPView.as_view()),
    path("reset-password", ResetPasswordView.as_view()),
]
