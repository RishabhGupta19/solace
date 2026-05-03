from django.urls import path
from .views import GalleryListCreateView, GalleryDeleteView, GalleryNoteView, PhotoServeView

urlpatterns = [
    path("photos", GalleryListCreateView.as_view()),
    path("photo/<str:photo_id>/", PhotoServeView.as_view()),
    path("photos/<str:photo_id>", GalleryDeleteView.as_view()),
    path("photos/<str:photo_id>/note", GalleryNoteView.as_view()),
]
