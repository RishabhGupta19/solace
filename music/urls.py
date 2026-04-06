from django.urls import path
from .views import MusicLibraryView, MusicSongDetailView

urlpatterns = [
    path("library",             MusicLibraryView.as_view()),
    path("library/",            MusicLibraryView.as_view()),
    path("library/<str:video_id>",  MusicSongDetailView.as_view()),
    path("library/<str:video_id>/", MusicSongDetailView.as_view()),
]
