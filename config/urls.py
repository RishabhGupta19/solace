from django.urls import path, include

urlpatterns = [
    path("api/auth/",         include("auth_app.urls")),
    path("api/couple/",       include("couples.urls")),
    path("api/assessment/",   include("assessment.urls")),
    path("api/goals/",        include("goals.urls")),
    path("api/goals",         include("goals.urls")),
    path("api/",              include("chat.urls")),
]
