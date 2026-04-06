from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("api/auth/",         include("auth_app.urls")),
    path("api/couple/",       include("couples.urls")),
    path("api/assessment/",   include("assessment.urls")),
    path("api/goals/",        include("goals.urls")),
    path("api/goals",         include("goals.urls")),
    path("api/music/",        include("music.urls")),
    path("api/music",         include("music.urls")),
    path("api/",              include("chat.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
